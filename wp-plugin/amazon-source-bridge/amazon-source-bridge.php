<?php
/**
 * Plugin Name:       Amazon Source Bridge
 * Description:       When a shopper searches for a product you don't stock, fetch a materialized version from your catalog service and render it inside WooCommerce. On order placed, the product becomes a real WC product tied to the order.
 * Version:           0.1.0
 * Requires PHP:      7.4
 * Requires at least: 6.0
 * Author:            you
 * Text Domain:       amazon-source-bridge
 */

defined( 'ABSPATH' ) || exit;

define( 'ASB_VERSION', '0.1.0' );
define( 'ASB_DIR', plugin_dir_path( __FILE__ ) );
define( 'ASB_URL', plugin_dir_url( __FILE__ ) );

require_once ASB_DIR . 'includes/settings.php';
require_once ASB_DIR . 'includes/api.php';
require_once ASB_DIR . 'includes/search.php';
require_once ASB_DIR . 'includes/product-page.php';
require_once ASB_DIR . 'includes/cart-order.php';

register_activation_hook( __FILE__, function () {
    asb_register_rewrites();
    flush_rewrite_rules();
} );

register_deactivation_hook( __FILE__, function () {
    flush_rewrite_rules();
} );

add_action( 'init', 'asb_register_rewrites' );
add_action( 'admin_notices', function () {
    if ( ! class_exists( 'WooCommerce' ) ) {
        echo '<div class="notice notice-error"><p><strong>Amazon Source Bridge</strong> requires WooCommerce to be active.</p></div>';
    }
    if ( ! asb_settings( 'api_url' ) || ! asb_settings( 'api_key' ) ) {
        echo '<div class="notice notice-warning"><p><strong>Amazon Source Bridge</strong>: set the API URL and API key in <a href="' . esc_url( admin_url( 'options-general.php?page=amazon-source-bridge' ) ) . '">Settings → Amazon Source Bridge</a>.</p></div>';
    }
} );
