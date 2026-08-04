<?php
defined( 'ABSPATH' ) || exit;

const IMAGECONV_SETTINGS_KEY = 'imageconv_settings';

function imageconv_settings( $field = null, $default = '' ) {
    $opts = get_option( IMAGECONV_SETTINGS_KEY, [] );
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
        'ImageConv',
        'ImageConv',
        'manage_options',
        'imageconv',
        'imageconv_render_settings_page'
    );
} );

add_action( 'admin_init', function () {
    register_setting(
        'imageconv_settings_group',
        IMAGECONV_SETTINGS_KEY,
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

function imageconv_render_settings_page() {
    if ( ! current_user_can( 'manage_options' ) ) {
        return;
    }
    ?>
    <div class="wrap">
        <h1>ImageConv</h1>
        <form method="post" action="options.php">
            <?php settings_fields( 'imageconv_settings_group' ); ?>
            <table class="form-table">
                <tr>
                    <th scope="row"><label for="imageconv_api_url">API URL</label></th>
                    <td>
                        <input type="url" id="imageconv_api_url" class="regular-text"
                               name="<?php echo esc_attr( IMAGECONV_SETTINGS_KEY ); ?>[api_url]"
                               value="<?php echo esc_attr( imageconv_settings( 'api_url' ) ); ?>"
                               placeholder="https://api.yourdomain.com" />
                        <p class="description">Base URL of the FastAPI materialization service (no trailing slash).</p>
                    </td>
                </tr>
                <tr>
                    <th scope="row"><label for="imageconv_api_key">API Key</label></th>
                    <td>
                        <input type="password" id="imageconv_api_key" class="regular-text"
                               name="<?php echo esc_attr( IMAGECONV_SETTINGS_KEY ); ?>[api_key]"
                               value="<?php echo esc_attr( imageconv_settings( 'api_key' ) ); ?>" />
                        <p class="description">Shared secret sent as the <code>X-API-Key</code> header.</p>
                    </td>
                </tr>
                <tr>
                    <th scope="row"><label for="imageconv_currency">Currency</label></th>
                    <td>
                        <input type="text" id="imageconv_currency" class="regular-text"
                               name="<?php echo esc_attr( IMAGECONV_SETTINGS_KEY ); ?>[currency]"
                               value="<?php echo esc_attr( imageconv_settings( 'currency', 'INR' ) ); ?>" />
                        <p class="description">Fallback currency when the catalog row omits it.</p>
                    </td>
                </tr>
            </table>
            <?php submit_button(); ?>
        </form>
    </div>
    <?php
}
