<?php
defined( 'ABSPATH' ) || exit;

/**
 * Low-level HTTP call to the materialization API. Returns decoded JSON or
 * WP_Error on failure. Never throws.
 */
function asb_api_request( $method, $path, $args = [] ) {
    $base = asb_settings( 'api_url' );
    $key  = asb_settings( 'api_key' );
    if ( ! $base || ! $key ) {
        return new WP_Error( 'asb_not_configured', 'Amazon Source Bridge is not configured.' );
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
        return new WP_Error( 'asb_http_' . $code, "API returned {$code}: {$detail}" );
    }
    return $data;
}

function asb_search( $query, $limit = 20 ) {
    return asb_api_request( 'GET', '/search', [ 'query' => [ 'q' => $query, 'limit' => $limit ] ] );
}

function asb_get_product( $asin ) {
    return asb_api_request( 'GET', '/product/' . rawurlencode( $asin ) );
}

function asb_materialize( $asin ) {
    return asb_api_request( 'POST', '/materialize/' . rawurlencode( $asin ) );
}
