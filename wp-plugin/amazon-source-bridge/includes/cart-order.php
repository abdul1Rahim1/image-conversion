<?php
defined( 'ABSPATH' ) || exit;

/**
 * Cart + order integration.
 *
 * "Add to cart" for a phantom product:
 *   1. Force-materialize via the API (bypass cache).
 *   2. Create a WC product as `draft` — invisible to the public shop.
 *   3. Add that product to the cart.
 *   4. Redirect to checkout.
 *
 * On order placed (`woocommerce_new_order`):
 *   Flip any draft phantom products in the order to `publish` so they
 *   become real products in the WooCommerce DB tied to that order.
 */

const ASB_META_ASIN         = '_asb_source_asin';
const ASB_META_DRAFT        = '_asb_phantom_draft';
const ASB_META_MATERIALIZED = '_asb_materialized_at';

add_action( 'template_redirect', function () {
    if ( ! isset( $_GET['asb_action'] ) || $_GET['asb_action'] !== 'add_to_cart' ) {
        return;
    }
    if ( ! isset( $_GET['asin'] ) ) {
        wp_die( 'Missing asin' );
    }
    $asin = sanitize_text_field( wp_unslash( $_GET['asin'] ) );
    $nonce = isset( $_GET['_wpnonce'] ) ? sanitize_text_field( wp_unslash( $_GET['_wpnonce'] ) ) : '';
    if ( ! wp_verify_nonce( $nonce, 'asb_add_to_cart_' . $asin ) ) {
        wp_die( 'Invalid nonce' );
    }
    if ( ! class_exists( 'WooCommerce' ) || ! WC()->cart ) {
        wp_die( 'WooCommerce not available' );
    }

    $data = asb_materialize( $asin );
    if ( is_wp_error( $data ) ) {
        wp_die( 'Could not prepare product: ' . esc_html( $data->get_error_message() ) );
    }
    $product = $data['product'] ?? null;
    if ( ! $product ) {
        wp_die( 'Product data missing' );
    }

    $product_id = asb_upsert_draft_product( $asin, $product );
    if ( is_wp_error( $product_id ) ) {
        wp_die( 'Could not create product: ' . esc_html( $product_id->get_error_message() ) );
    }

    WC()->cart->add_to_cart( $product_id, 1 );
    wp_safe_redirect( wc_get_checkout_url() );
    exit;
} );

/**
 * Find an existing draft phantom product for this ASIN or create one.
 * Kept as draft until the order is placed.
 */
function asb_upsert_draft_product( $asin, $product ) {
    $existing = get_posts( [
        'post_type'   => 'product',
        'post_status' => [ 'draft', 'private' ],
        'meta_key'    => ASB_META_ASIN,
        'meta_value'  => $asin,
        'numberposts' => 1,
        'fields'      => 'ids',
    ] );
    $product_id = $existing ? (int) $existing[0] : 0;

    if ( ! $product_id ) {
        $product_id = wp_insert_post( [
            'post_title'   => wp_strip_all_tags( $product['Title'] ?? $product['title'] ?? '' ),
            'post_content' => (string) ( $product['Category'] ?? $product['description'] ?? '' ),
            'post_status'  => 'draft',
            'post_type'    => 'product',
        ], true );
        if ( is_wp_error( $product_id ) ) {
            return $product_id;
        }
        wp_set_object_terms( $product_id, 'simple', 'product_type' );
    }

    $price = (float) ( $product['Price (INR)'] ?? $product['price'] ?? 0 );

    update_post_meta( $product_id, '_regular_price', $price );
    update_post_meta( $product_id, '_price', $price );
    update_post_meta( $product_id, '_manage_stock', 'no' );
    update_post_meta( $product_id, '_stock_status', 'instock' );
    update_post_meta( $product_id, '_virtual', 'no' );
    update_post_meta( $product_id, '_visibility', 'hidden' );

    update_post_meta( $product_id, ASB_META_ASIN, $asin );
    update_post_meta( $product_id, ASB_META_DRAFT, '1' );
    update_post_meta( $product_id, ASB_META_MATERIALIZED, time() );

    $img = $product['image_url'] ?? $product['variant_1_url'] ?? '';
    if ( $img ) {
        asb_attach_external_image( $product_id, $img );
    }

    return $product_id;
}

/**
 * Sideload the R2 image into the WP media library and set as product image.
 * Idempotent: if we've already attached an image for this URL, skip.
 */
function asb_attach_external_image( $product_id, $image_url ) {
    if ( get_post_thumbnail_id( $product_id ) ) {
        return;
    }
    require_once ABSPATH . 'wp-admin/includes/media.php';
    require_once ABSPATH . 'wp-admin/includes/file.php';
    require_once ABSPATH . 'wp-admin/includes/image.php';

    $tmp = download_url( $image_url, 30 );
    if ( is_wp_error( $tmp ) ) {
        return;
    }
    $file = [
        'name'     => basename( parse_url( $image_url, PHP_URL_PATH ) ) ?: 'product.webp',
        'tmp_name' => $tmp,
    ];
    $attachment_id = media_handle_sideload( $file, $product_id );
    if ( is_wp_error( $attachment_id ) ) {
        @unlink( $tmp );
        return;
    }
    set_post_thumbnail( $product_id, $attachment_id );
}

/**
 * When any order is created, publish the phantom draft products it contains.
 * That's the moment the product becomes real in the WooCommerce DB.
 */
add_action( 'woocommerce_new_order', function ( $order_id ) {
    $order = wc_get_order( $order_id );
    if ( ! $order ) {
        return;
    }
    foreach ( $order->get_items() as $item ) {
        $pid = $item->get_product_id();
        if ( get_post_meta( $pid, ASB_META_DRAFT, true ) === '1' ) {
            wp_update_post( [ 'ID' => $pid, 'post_status' => 'publish' ] );
            update_post_meta( $pid, ASB_META_DRAFT, '0' );
        }
    }
} );

/**
 * Nightly cleanup: delete phantom drafts older than 24h that never got ordered.
 */
add_action( 'asb_cleanup_drafts', function () {
    $cutoff = time() - DAY_IN_SECONDS;
    $ids = get_posts( [
        'post_type'   => 'product',
        'post_status' => 'draft',
        'meta_query'  => [
            [ 'key' => ASB_META_DRAFT, 'value' => '1' ],
            [ 'key' => ASB_META_MATERIALIZED, 'value' => $cutoff, 'compare' => '<', 'type' => 'NUMERIC' ],
        ],
        'numberposts' => 200,
        'fields'      => 'ids',
    ] );
    foreach ( $ids as $id ) {
        wp_delete_post( $id, true );
    }
} );

if ( ! wp_next_scheduled( 'asb_cleanup_drafts' ) ) {
    wp_schedule_event( time() + 3600, 'daily', 'asb_cleanup_drafts' );
}
