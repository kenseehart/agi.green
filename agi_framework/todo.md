- controlled exception handling (exception=None)
- info bot (avatar, name, color, upload image)
- rabbitmq swarm

- user/session management
  - id
  - node per user/session
    - http -> create nodes
    - explicitly connect for chat
      - chat channels -> mq

- game lobby
  - intent to play
  - notifications
  - md ui dumps

- agent
  - hidden agent
  - speak when spoken to (hidden agent in control)

- error handling
  - resume interrupted websocket
  - disconnect failed protocols if necessary, but keep the rest going
  - persistent protocol state
    - resume chat
    - resume game


