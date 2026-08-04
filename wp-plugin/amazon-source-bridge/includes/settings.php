<?php
defined( 'ABSPATH' ) || exit;

const ASB_SETTINGS_KEY = 'asb_settings';

function asb_settings( $field = null, $default = '' ) {
    $opts = get_option( ASB_SETTINGS_KEY, [] );
    if ( ! is_array( $opts ) ) {
        $opts = [];
    }
    if ( $field === null ) {
        return $opts;
    }
    return isset( $opts[ $field ] ) ? $opts[ $field ] : $default;
}

add_action( 'admin_menu', function () {
    add_options_page(
        'Amazon Source Bridge',
        'Amazon Source Bridge',
        'manage_options',
        'amazon-source-bridge',
        'asb_render_settings_page'
    );
} );

add_action( 'admin_init', function () {
    register_setting(
        'asb_settings_group',
        ASB_SETTINGS_KEY,
        [
            'sanitize_callback' => function ( $input ) {
                $out = [];
                $out['api_url']  = isset( $input['api_url'] ) ? untrailingslashit( esc_url_raw( $input['api_url'] ) ) : '';
                $out['api_key']  = isset( $input['api_key'] ) ? sanitize_text_field( $input['api_key'] ) : '';
                $out['currency'] = isset( $input['currency'] ) ? sanitize_text_field( $input['currency'] ) : 'INR';
                return $out;
            },
        ]
    );
} );

function asb_render_settings_page() {
    if ( ! current_user_can( 'manage_options' ) ) {
        return;
    }
    ?>
    <div class="wrap">
        <h1>Amazon Source Bridge</h1>
        <form method="post" action="options.php">
            <?php settings_fields( 'asb_settings_group' ); ?>
            <table class="form-table">
                <tr>
                    <th scope="row"><label for="asb_api_url">API URL</label></th>
                    <td>
                        <input type="url" id="asb_api_url" class="regular-text"
                               name="<?php echo esc_attr( ASB_SETTINGS_KEY ); ?>[api_url]"
                               value="<?php echo esc_attr( asb_settings( 'api_url' ) ); ?>"
                               placeholder="https://api.yourdomain.com" />
                        <p class="description">Base URL of the FastAPI materialization service (no trailing slash).</p>
                    </td>
                </tr>
                <tr>
                    <th scope="row"><label for="asb_api_key">API Key</label></th>
                    <td>
                        <input type="password" id="asb_api_key" class="regular-text"
                               name="<?php echo esc_attr( ASB_SETTINGS_KEY ); ?>[api_key]"
                               value="<?php echo esc_attr( asb_settings( 'api_key' ) ); ?>" />
                        <p class="description">Shared secret sent as the <code>X-API-Key</code> header.</p>
                    </td>
                </tr>
                <tr>
                    <th scope="row"><label for="asb_currency">Currency</label></th>
                    <td>
                        <input type="text" id="asb_currency" class="regular-text"
                               name="<?php echo esc_attr( ASB_SETTINGS_KEY ); ?>[currency]"
                               value="<?php echo esc_attr( asb_settings( 'currency', 'INR' ) ); ?>" />
                        <p class="description">Fallback currency when the catalog row omits it.</p>
                    </td>
                </tr>
            </table>
            <?php submit_button(); ?>
        </form>
    </div>
    <?php
}
