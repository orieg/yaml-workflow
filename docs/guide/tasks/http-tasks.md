# HTTP Tasks

This section covers the built-in tasks for HTTP operations.

## HTTP Request Task

The `http_request` task makes HTTP requests to external services.

### Parameters

- `url` (string, required): The URL to request
- `method` (string, default: "GET"): HTTP method (GET, POST, PUT, DELETE, etc.)
- `headers` (dict, optional): Request headers
- `params` (dict, optional): Query parameters
- `data` (any, optional): Request body for POST/PUT requests
- `json` (any, optional): JSON request body (sets Content-Type)
- `timeout` (integer, default: 30): Request timeout in seconds
- `verify_ssl` (boolean, default: true): Whether to verify SSL certificates
- `auth` (dict, optional): Authentication credentials
- `retry` (dict, optional): Retry configuration

### Examples

#### Basic GET Request

```yaml
- name: fetch_data
  task: http_request
  params:
    url: "https://api.example.com/data"
    method: GET
    headers:
      Authorization: "Bearer {{ api_token }}"
  output_var: response_data
```

#### POST Request with JSON

```yaml
- name: create_resource
  task: http_request
  params:
    url: "https://api.example.com/resources"
    method: POST
    json:
      name: "{{ resource_name }}"
      type: "example"
    headers:
      Authorization: "Bearer {{ api_token }}"
  output_var: created_resource
```

#### Request with Query Parameters

```yaml
- name: search_items
  task: http_request
  params:
    url: "https://api.example.com/search"
    method: GET
    params:
      q: "{{ search_query }}"
      limit: 10
      offset: 0
  output_var: search_results
```

#### Request with Retry Logic

```yaml
- name: reliable_fetch
  task: http_request
  params:
    url: "https://api.example.com/data"
    method: GET
    retry:
      max_attempts: 3
      delay: 5
      backoff_factor: 2
      retry_on:
        - 429  # Too Many Requests
        - 503  # Service Unavailable
  output_var: response_data
```

#### File Upload

```yaml
- name: upload_file
  task: http_request
  params:
    url: "https://api.example.com/upload"
    method: POST
    files:
      file:
        path: "{{ file_path }}"
        content_type: "application/octet-stream"
    headers:
      Authorization: "Bearer {{ api_token }}"
  output_var: upload_response
```

## API Authentication

### Basic Auth

```yaml
- name: authenticated_request
  task: http_request
  params:
    url: "https://api.example.com/secure"
    method: GET
    auth:
      type: basic
      username: "{{ username }}"
      password: "{{ password }}"
```

### Bearer Token

```yaml
- name: token_request
  task: http_request
  params:
    url: "https://api.example.com/data"
    method: GET
    headers:
      Authorization: "Bearer {{ access_token }}"
```

## Error Handling

The task automatically handles common HTTP errors:

- Retries on configurable status codes
- Timeout handling
- SSL verification options
- Custom error responses

```yaml
- name: robust_request
  task: http_request
  params:
    url: "https://api.example.com/data"
    method: GET
    timeout: 60
    verify_ssl: true
    retry:
      max_attempts: 3
      delay: 5
      retry_on:
        - 429
        - 500
        - 502
        - 503
        - 504
  on_error:
    action: continue
    output:
      status: error
      message: "Failed to fetch data" 