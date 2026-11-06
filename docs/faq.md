# Frequently asked questions

## Why does showing a layer during the simulation not show its bodies?

The eye icon works, but the bodies on the layer stay invisible. Newton decides at **Start** which bodies take part in the simulation, and by default it leaves out most hidden ones.

When you press **Start**, Newton builds a temporary copy of the model. Hidden groups and groups on hidden layers follow **Preferences → Newton → Simulation → Hidden geometry → Include**:

- **When needed** (the default) keeps a hidden body only if a visible body depends on it (as its reference body, attachment, connection or coupling) and keeps hidden static bodies as surroundings. All other hidden bodies are not copied, so large models start faster.
- **Always** copies and simulates every hidden body.
- **Never** leaves every hidden body out.

A body that was left out does not exist in the temporary copy. Showing its layer during the simulation changes the layer, but there is nothing on it to draw. Hiding a layer during the simulation works, because its bodies are in the copy.

To see those bodies in the simulation, do one of the following:

- Show the layers before you press **Start**.
- Set **Include** to **Always**. Every hidden body is then simulated and can be shown and hidden while the simulation runs; the start takes longer on large models.

Details: [manual](manual.md#limits).
