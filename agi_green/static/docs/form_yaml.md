# YAML Form Markdown Specification

## Overview
YAML forms provide a declarative way to create interactive forms in markdown. These forms can submit via HTTP POST or WebSocket. Based on the Vueform library, these forms support a wide range of input types and validation rules.

## `form-yaml`

You can use YAML to define forms. The remaining examples will use this format.

````code
```form-yaml
id: form_unique_id
schema:
  field_name:
    type: input_type
    label: Field Label
    # ... additional field properties
```
````

## `form-json`

You can also use JSON to define forms.
````code
```form-json
{
  "id": "form_unique_id",
  "schema": {
    "field_name": {
      "type": "input_type",
      "label": "Field Label"
    }
  }
}
```
````

## Common Properties
All fields can include these properties:
- `type`: The type of input field
- `label`: Display label for the field
- `default`: Default value
- `placeholder`: Placeholder text
- `disabled`: Boolean to disable the field
- `hidden`: Boolean to hide the field
- `submits`: Boolean to trigger form submission on change
- `ws_send`: String specifying WebSocket command name for real-time updates

## Field Types

### Text Input
```yaml
username:
  type: text
  label: Username
  placeholder: Enter username
```

### Password
```yaml
password:
  type: password
  label: Password
  placeholder: Enter password
```

### Radio Group
```yaml
options:
  type: radiogroup
  label: Select Option
  items:
    - value: option1
      label: Option 1
    - value: option2
      label: Option 2
  ws_send: option_selected # Sends updates via WebSocket
```

### Checkbox
```yaml
agree:
  type: checkbox
  label: I agree to terms
```

### Select/Dropdown
```yaml
country:
  type: select
  label: Country
  items:
    - value: us
      label: United States
    - value: uk
      label: United Kingdom
```

### Hidden Field
```yaml
form_id:
  type: hidden
  default: unique_id
```

### Button
```yaml
submit:
  type: button
  label: Submit
  submits: true # HTTP POST
  ws_send: form_submit # WebSocket
```

## WebSocket Integration

Fields with `ws_send` property will send real-time updates via WebSocket:

```yaml
id: my_form
schema:
  selection:
    type: radiogroup
    label: Choose Option
    items:
      - value: a
        label: Option A
      - value: b
        label: Option B
    ws_send: selection_made # WebSocket command name
```

When changed, sends:
```json
{
  "cmd": "selection_made",
  "form_id": "my_form",
  "data": {
    "selection": "a",
    "form_id": "my_form"
  }
}
```

A python handler can be defined to process the WebSocket messages:

```python
@ws_cmd("selection_made")
def handle_selection_made(data):
    print(data)
```

## Complete Example
```yaml
id: user_preferences
schema:
  theme:
    type: radiogroup
    label: Theme
    items:
      - value: light
        label: Light Theme
      - value: dark
        label: Dark Theme
    ws_send: theme_changed
  notifications:
    type: checkbox
    label: Enable Notifications
    default: true
  submit:
    type: button
    label: Save Preferences
    submits: true
```

## Form Submission Patterns

Forms support two types of submission patterns that can be used independently or together:

### 1. Traditional Form Submit
Uses HTTP POST to submit the entire form:

```yaml
id: login_form
schema:
  username:
    type: text
    label: Username
  password:
    type: password
    label: Password
  submit:
    type: button
    label: Login
    submits: true  # Triggers HTTP POST
```

When submitted, sends POST to `/vueform/process`:
```json
{
  "username": "user123",
  "password": "********",
  "form_id": "login_form"
}
```

Python handler:
```python
@protocol_handler
async def on_http_vueform_process(self, form_id: str, **kwargs):
    """Handle form POST submission"""
    logger.info(f"vueform_process {form_id}: {kwargs}")
    await self.handle_mesg(form_id, **kwargs)
    return "OK"
```

### 2. Real-time Updates
Uses WebSocket to send immediate updates when field values change:

```yaml
id: preferences
schema:
  theme:
    type: radiogroup
    label: Theme
    items:
      - value: light
        label: Light
      - value: dark
        label: Dark
    ws_send: theme_changed  # Triggers WebSocket message on change
```

When changed, sends WebSocket message:
```json
{
  "cmd": "theme_changed",
  "form_id": "preferences",
  "data": {
    "theme": "dark",
    "form_id": "preferences"
  }
}
```

Python handler:
```python
@protocol_handler
async def on_ws_theme_changed(self, data: dict):
    """Handle real-time theme updates"""
    theme = data['data']['theme']
    await self.update_theme(theme)
```

### Combined Pattern
You can use both patterns together for maximum flexibility:

```yaml
id: user_settings
schema:
  notifications:
    type: radiogroup
    label: Notifications
    items:
      - value: all
        label: All
      - value: important
        label: Important Only
      - value: none
        label: None
    ws_send: notifications_changed  # Immediate update
  email:
    type: text
    label: Email
  submit:
    type: button
    label: Save All Settings
    submits: true  # Final submission
```

This allows for:
1. Immediate UI updates via WebSocket when notification preference changes
2. Validation and permanent storage of all settings on final submit