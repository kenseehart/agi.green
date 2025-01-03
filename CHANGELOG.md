# Changelog

All notable changes to this project will be documented in this file.

## [0.2.7] - 2024-12-18

### Added
- Azure user identity and photo support

## [0.2.6] - 2024-11-22

### Added
- send ws message back to server on button selection changes (no submit button required)

### Fixed
- scrollbar glitch

## [0.2.5] - 2024-11-20

### Added
- Bug fix for ws connection reset - duplicate message queue

## [0.2.4] - 2024-11-19

### Added
- Abstract MQ protocol with three implementations
- Support for Azure Service Bus, RabbitMQ, and in-process queues
- Environment variable `MQ_PROTOCOL=azure|rabbitmq|inprocess` to force specific implementation
    Default is to use what is detected at startup:
    - azure: Azure Service Bus
    - rabbitmq: RabbitMQ
    - inprocess: in-process queues suitable for small-scale deployments (single process)

## [0.2.3] - 2024-11-17

### Added
- `ws_send` markdown hyperlink protocol to send ws message back to server

``` markdown
[Do something](ws_send:something?id=123&location='somewhere')
```
*...which would be handled by...*

```python
@protocol_handler
async def on_ws_something(self, id: int, location: str):
    ...
```

- Colorize python code blocks in markdown

[0.2.5]: https://github.com/kenseehart/agi.green/compare/v0.2.4...v0.2.5
[0.2.4]: https://github.com/kenseehart/agi.green/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/kenseehart/agi.green/compare/v0.2.2...v0.2.3
