# Changelog

## [0.4.3] - 2025-06-10

### Fixed
- mq protocol handler should use non-blocking queue operations

## [0.4.2] - 2025-03-22

### Fixed
- Use cloudflare polyfill
- Fixed duplicate websocket connection on loading (regression in 0.4.1)

## [0.4.1] - 2025-03-20

### Fixed
- Duplicate websocket connection on loading

## [0.4.0] - 2025-03-17

### Added
- Support for application vite build
- set_md command (write to named MarkdownVue component without requiring a tab)
- better resize handling

### Fixed
- scrollbar glitch

## [0.3.6] - 2025-02-28

### Changed
- Omit welcome message if config option `welcome_message` is None

## [0.3.5] - 2025-02-17

### Config
- Increased max upload size to 10GB

### Removed
- Assorted cruft

## [0.3.4] - 2025-01-22

### Added
- `http_response` protocol handler to handle post-processing of http responses

## [0.3.3] - 2025-01-22

### Added
- File drop support

## [0.3.2] - 2025-01-13

- socket id channels (isolation of distinct browser pages)

## [0.3.1] - 2025-01-08

- minor fixes

## [0.3.0] - 2025-01-05

### Added
- Support multiple sockets on one session

## [0.2.9] - 2025-01-03

### Added
- protocol_file to handle dynamic file changes
- elapsed_time markdown protocol `[since|2025-01-03T12:00:00Z]` -> '1m23s'

## [0.2.8] - 2024-12-18

### Added
- Azure user identity and photo support

## [0.2.7] - 2024-12-02

### Fixed
- Multiple sessions stability improvements

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

[0.4.0]: https://github.com/kenseehart/agi.green/compare/v0.3.6...v0.4.0
[0.3.6]: https://github.com/kenseehart/agi.green/compare/v0.3.5...v0.3.6
[0.3.5]: https://github.com/kenseehart/agi.green/compare/v0.3.4...v0.3.5
[0.3.4]: https://github.com/kenseehart/agi.green/compare/v0.3.3...v0.3.4
[0.3.3]: https://github.com/kenseehart/agi.green/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/kenseehart/agi.green/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/kenseehart/agi.green/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/kenseehart/agi.green/compare/v0.2.9...v0.3.0
[0.2.9]: https://github.com/kenseehart/agi.green/compare/v0.2.8...v0.2.9
[0.2.8]: https://github.com/kenseehart/agi.green/compare/v0.2.7...v0.2.8
[0.2.7]: https://github.com/kenseehart/agi.green/compare/v0.2.6...v0.2.7
[0.2.6]: https://github.com/kenseehart/agi.green/compare/v0.2.5...v0.2.6
[0.2.5]: https://github.com/kenseehart/agi.green/compare/v0.2.4...v0.2.5
[0.2.4]: https://github.com/kenseehart/agi.green/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/kenseehart/agi.green/compare/v0.2.2...v0.2.3
