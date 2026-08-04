<?php
defined( 'ABSPATH' ) || exit;

/**
 * Inject external catalog hits into the WooCommerce search page. Runs after
 * the native product loop, so real in-stock products appear first and
 * externally-materialized ones appear underneath. Uses WooCommerce's own
 * .products / .product classes so the current theme's CSS styles them.
 */
add_action( 'woocommerce_after_shop_loop', 'asb_render_external_matches', 20 );
add_action( 'woocommerce_no_products_found', 'asb_render_external_matches', 20 );

function asb_render_external_matches() {
    if ( ! is_search() ) {
        return;
    }
    $q = trim( (string) get_search_query() );
    if ( $q === '' ) {
        return;
    }
    $result = asb_search( $q, 20 );
    if ( is_wp_error( $result ) || empty( $result['hits'] ) ) {
        return;
    }

    $currency = asb_settings( 'currency', 'INR' );
    echo '<div class="asb-external-matches">';
    echo '<h2>' . esc_html( sprintf( 'More matches for "%s"', $q ) ) . '</h2>';
    echo '<ul class="products columns-4">';
    foreach ( $result['hits'] as $hit ) {
        $asin  = esc_attr( $hit['asin'] );
        $title = esc_html( $hit['title'] );
        $price = isset( $hit['price'] ) ? $hit['price'] : null;
        $cur   = ! empty( $hit['currency'] ) ? $hit['currency'] : $currency;
        $img   = ! empty( $hit['source_image_url'] ) ? esc_url( $hit['source_image_url'] ) : '';
        $url   = esc_url( home_url( '/asb/p/' . $asin ) );

        echo '<li class="product asb-product">';
        echo '<a href="' . $url . '">';
        if ( $img ) {
            echo '<img src="' . $img . '" alt="" loading="lazy" style="width:100%;height:auto;" />';
        }
        echo '<h2 class="woocommerce-loop-product__title">' . $title . '</h2>';
        if ( $price !== null ) {
            echo '<span class="price"><span class="woocommerce-Price-amount amount">' .
                esc_html( $cur ) . ' ' . esc_html( number_format_i18n( $price, 2 ) ) .
                '</span></span>';
        }
        echo '<span class="button">View</span>';
        echo '</a>';
        echo '</li>';
    }
    echo '</ul>';
    echo '</div>';
}
