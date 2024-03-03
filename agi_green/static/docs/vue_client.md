# AGI Green Vue client

The client is designed to have minimal business logic, and to be driven by an app running on the python server via websockets, instead of a client app requesting data via REST API.

The client provides a few general purpose components for use by the python app.

## Chat.vue

A general purpose chat UI. For chatting with humans and agents.

Messages are handled by:

- `ws_set_user_data`: sets avatar and other user data
- `ws_append_chat`: adds a message

User chat input is sent to the server app via `send_ws('chat_input', 'cpontent')`, and echoed by the server.

## Markdown.vue

Displays and interacts with md documents.

- mathjax
- mermaid
- forms (a custom md extension to provide interactive forms)

### Forms example:

```form-json
{
  "id": "login_json",
  "schema": {
    "h2": {
      "type": "static",
      "tag": "h3",
      "content": "JSON login form"
    },
    "user": {
      "type": "text",
      "label": "Username"
    },
    "password": {
      "type": "text",
      "inputType": "password",
      "label": "Password"
    }
  }
}
```

```form-yaml
id: login_yaml
schema:
  h2:
    type: static
    tag: h3
    content: YAML login form
  user:
    type: text
    label: Username
  password:
    type: text
    inputType: password
    label: Password
```

### Mermaid example:
```mermaid
graph LR
subgraph A
A0
A1
A2
A3
end
subgraph B
B0
B1
B2
B3
B4
end
A0 -- w0 --> B0
A0 -- w1 --> B1
A0 -- w2 --> B3
A1 -- w1 --> B0
A1 -- w3 --> B3
A1 -- w2 --> B2
A2 -- w0 --> B0
A2 -- w0 --> B2
A2 -- w3 --> B1
A2 -- w4 --> B3
A2 -- w1 --> B4
A3 -- w2 --> B3
A3 -- w4 --> B4
A3 -- w1 --> B1

```

### MathML example:

$$ B_i = \phi(\sum_j A[p_{ij}]w[q_{ij}]) $$


## GameIO.vue

(to be ported from obsolete code from before vue conversion)

- play board games with user

