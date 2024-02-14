# How models.yaml works


``` yaml
models:
  y9_db:
    game: y9
    class: YDB

  y15_db:
    game: y15
    class: YDB

  y9_50_50_50:
    game: y9
    class: SimpleModel
    hidden_layers:
      - 50
      - 50
      - 50
```

`class` specifies a class defined in `model.py`.
`game` is loaded from registered games, in this case that would one of the y variants. The resulting game object is the first argument to *class*.`__init__`
All of the other args are passed as named arguments to *class*.`__init__()` and any args not consumed are then forwaded to `make_layers()`.

## Suffixes

``` yaml
The suffix mechanism expands a model into several variants

suffixes:
  _*:
    _x:
      shared: False
    _v15:
      distribution_multiplier: 1.5
    _v20:
      distribution_multiplier: 2.0
    _v25:
      distribution_multiplier: 2.5

models:
  y15_s1_*:
    game: y15
    class: SymmetricModel
    shared: True

    local_fields:
      edge_fields: 2
      mid_fields: 5
    hidden_layers:
      - [0, (1, a), (1, b), c, d, e]
      - [0, 1, a, b, c, d]
    color_naive: 1
```

This generates definitions for `y15_s1_x`, `y15_s1_v15`, `y15_s1_v20`, `y15_s1_v25` which are all clones of virtual model `y15_s1_*` with respective attributes `shared` amd `distribution_multiplier`. However, `y15_s1_*` itself is not defined.


