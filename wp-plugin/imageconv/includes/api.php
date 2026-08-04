<?php
defined( 'ABSPATH' ) || exit;

/**
 * Low-level HTTP call to the materialization API. Returns decoded JSON or
 * WP_Error on failure. Never throws.
 */
function imageconv_api_request( $method, $path, $args = [] ) {
    $base = imageconv_settings( 'api_url' );
    $key  = imageconv_settings( 'api_key' );
    if ( ! $base || ! $key ) {
        return new WP_Error( 'imageconv_not_configured', 'ImageConv is not configured.' );
    }

    $url = trailingslashit( $base ) . ltrim( $path, '/' );
    $headers = [ 'X-API-Key' => $key, 'Accept' => 'application/json' ];

    $params = [
        'method'  => strtoupper( $method ),
        'headers' => $headers,
        'timeout' => 20,
    ];
    if ( ! empty( $args['query'] ) ) {
        $url = add_query_arg( $args['query'], $url );
    }
    if ( ! empty( $args['body'] ) ) {
        $params['body']    = wp_json_encode( $args['body'] );
        $params['headers']['Content-Type'] = 'application/json';
    }

    $response = wp_remote_request( $url, $params );
    if ( is_wp_error( $response ) ) {
        return $response;
    }
    $code = wp_remote_retrieve_response_code( $response );
    $body = wp_remote_retrieve_body( $response );
    $data = json_decode( $body, true );
    if ( $code >= 400 ) {
        $detail = is_array( $data ) && isset( $data['detail'] ) ? $data['detail'] : $body;
        return new WP_Error( 'imageconv_http_' . $code, "API returned {$code}: {$detail}" );
    }
    return $data;
}

function imageconv_search( $query, $limit = 20 ) {
    return imageconv_api_request( 'GET', '/search', [ 'query' => [ 'q' => $query, 'limit' => $limit ] ] );
}

function imageconv_get_product( $asin ) {
    return imageconv_api_request( 'GET', '/product/' . rawurlencode( $asin ) );
}

function imageconv_materialize( $asin ) {
    return imageconv_api_request( 'POST', '/materialize/' . rawurlencode( $asin ) );
}
