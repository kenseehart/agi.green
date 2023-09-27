
# Game Communication Protocol

This protocol is designed for communication between the game server and the UI using the agi.green chat framework. It ensures the UI doesn't need prior knowledge of any specific game or the kinds of pieces involved.

An abstract base class for game rules and assets is provided.

## Initialization Message

This message is responsible for setting up the board, defining locations, and introducing available pieces.


```json
{
    "action": "initialize",
    "boardImage": "board_filename.jpg",
    "locations": [
        {"id": "locationA", "coords": [0.5, 0.2]},
        {"id": "locationB", "coords": [0.1, 0.3]},
        ...
    ],
    "pieces": [
        {"id": "piece1", "image": "piece1_filename.png", "desc": "Description for piece1"},
        {"id": "piece2", "image": "piece2_filename.png", "desc": "Description for piece2"},
        ...
    ]
}
```

### Parameters:

- `boardImage`: The image file representing the game board.

- `locations`: A list of location objects, each containing:
    - `id`: The unique identifier for the location.
    - `coords`: Relative coordinates of the location on the board, ranging from `(0,0)` to `(1,1)`.

- `pieces`: A list of piece objects, each encompassing:
    - `id`: The unique identifier for the piece.
    - `image`: The image file representing the piece.
    - `desc`: (opt) A brief description, which can be useful for tool tips or other UI enhancements.
    - `anchor`: (opt) point within image `[0:1, 0:1]` that maps to location coordinates. Default centered `[0.5, 0.5]`.

This structure allows easy extensions for future properties, be it aesthetic enhancements or gameplay mechanics.


### Parameters:

- `boardImage`: The image file that represents the game board.
- `locations`: A dictionary mapping unique location IDs to their relative coordinates on the board, within the range `[0:1, 0:1]`.
- `pieces`: A dictionary mapping piece identifiers to their associated image files.

## Action Messages

These messages convey game actions like moving, placing, and removing pieces.

### Moving a piece:

To move an existing piece from one location to another.

```json
{
    "action": "move",
    "piece": "piece1",
    "from": "locationA",
    "to": "locationB"
}
```

### Placing a new piece:

To place a new piece on the board. The absence of a "from" field indicates this action.

```json
{
    "action": "move",
    "piece": "piece2",
    "to": "locationC"
}
```

### Removing a piece:

This can be interpreted as moving a piece to a null location. Alternatively, a distinct action can be used for clarity.

```json
{
    "action": "remove",
    "piece": "piece1",
    "from": "locationA"
}
```

### Notes:

1. In the case of placing a new piece on the board, only the `piece` and `to` parameters are used. The absence of `from` implies it's a new placement.
2. For removing a piece, either omit the `to` parameter or utilize the distinct `remove` action.



