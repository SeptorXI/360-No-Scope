package steven.armordisplays;

import com.hypixel.hytale.component.Component;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/** Nonserialized link used to clean visual props if their block disappears. */
public final class VisualMarker implements Component<EntityStore> {
    final Ref<ChunkStore> source;
    public VisualMarker(Ref<ChunkStore> source) { this.source = source; }
    public Ref<ChunkStore> source() { return source; }
    @Override public Component<EntityStore> clone() { return new VisualMarker(source); }
}
