<?php
defined( 'ABSPATH' ) || exit;

/**
 * Custom URL /imageconv/p/{asin} → phantom product page. Polls the API for the
 * materialized product; while it's still processing we render a lightweight
 * "preparing" state that auto-refreshes.
 */
function imageconv_register_rewrites() {
    add_rewrite_rule( '^imageconv/p/([A-Za-z0-9]+)/?$', 'index.php?imageconv_asin=$matches[1]', 'top' );
    add_rewrite_tag( '%imageconv_asin%', '([A-Za-z0-9]+)' );
}

add_filter( 'query_vars', function ( $vars ) {
    $vars[] = 'imageconv_asin';
    return $vars;
} );

add_action( 'template_redirect', function () {
    $asin = get_query_var( 'imageconv_asin' );
    if ( ! $asin ) {
        return;
    }
    imageconv_render_phantom_product_page( sanitize_text_field( $asin ) );
    exit;
} );

function imageconv_render_phantom_product_page( $asin ) {
    $data = imageconv_get_product( $asin );
    if ( is_wp_error( $data ) ) {
        status_header( 502 );
        get_header();
        echo '<main class="site-main"><div class="container" style="padding:2rem 1rem;">';
        echo '<h1>Product unavailable</h1><p>' . esc_html( $data->get_error_message() ) . '</p>';
        echo '</div></main>';
        get_footer();
        return;
    }

    $status  = isset( $data['status'] ) ? $data['status'] : 'unknown';
    $product = isset( $data['product'] ) ? $data['product'] : null;

    get_header();
    echo '<div id="primary" class="content-area primary"><main id="main" class="site-main">';
    echo '<div class="ast-container">';

    if ( $status !== 'ready' || ! $product ) {
        echo '<meta http-equiv="refresh" content="6" />';
        echo '<div class="entry-content" style="text-align:center;padding:4rem 1rem;">';
        echo '<h1>Preparing your product…</h1>';
        echo '<p>This usually takes under a minute. This page will refresh automatically.</p>';
        echo '<p style="opacity:.7">Status: <code>' . esc_html( $status ) . '</code></p>';
        echo '</div>';
    } else {
        imageconv_render_ready_product( $asin, $product );
    }

    echo '</div></main></div>';
    get_footer();
}

function imageconv_render_ready_product( $asin, $product ) {
    $title = $product['Title'] ?? ( $product['title'] ?? '' );
    $desc  = $product['Category'] ?? ( $product['description'] ?? '' );
    $img   = $product['image_url'] ?? ( $product['variant_1_url'] ?? '' );
    $price = $product['Price (INR)'] ?? ( $product['price'] ?? null );
    $cur   = 'INR';
    if ( isset( $product['Delivery']['price']['currency'] ) ) {
        $cur = $product['Delivery']['price']['currency'];
    }

    $add_url = wp_nonce_url(
        add_query_arg( [
            'imageconv_action' => 'add_to_cart',
            'asin'       => $asin,
        ], home_url( '/' ) ),
        'imageconv_add_to_cart_' . $asin
    );

    echo '<div class="woocommerce">';
    echo '<div class="product type-product">';

    echo '<div class="woocommerce-product-gallery woocommerce-product-gallery--with-images images">';
    if ( $img ) {
        echo '<figure class="woocommerce-product-gallery__wrapper">';
        echo '<div class="woocommerce-product-gallery__image">';
        echo '<img src="' . esc_url( $img ) . '" alt="' . esc_attr( $title ) . '" />';
        echo '</div>';
        echo '</figure>';
    }
    echo '</div>';

    echo '<div class="summary entry-summary">';
    echo '<h1 class="product_title entry-title">' . esc_html( $title ) . '</h1>';
    if ( $price !== null ) {
        echo '<p class="price"><span class="woocommerce-Price-amount amount">' .
            esc_html( $cur ) . ' ' . esc_html( number_format_i18n( (float) $price, 2 ) ) .
            '</span></p>';
    }
    echo '<div class="woocommerce-product-details__short-description">';
    echo wp_kses_post( wpautop( $desc ) );
    echo '</div>';
    echo '<form class="cart" method="get" action="' . esc_url( $add_url ) . '">';
    echo '<a href="' . esc_url( $add_url ) . '" class="single_add_to_cart_button button alt">Add to cart</a>';
    echo '</form>';
    echo '</div>';

    echo '</div>';
    echo '</div>';
}
