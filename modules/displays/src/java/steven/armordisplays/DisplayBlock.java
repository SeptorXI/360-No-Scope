package steven.armordisplays;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.Component;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.SimpleItemContainer;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.util.ArrayList;
import java.util.List;

/** Only Kind/Style persist. Native ItemContainerBlock owns every real item. */
public final class DisplayBlock implements Component<ChunkStore> {
    public static final BuilderCodec<DisplayBlock> CODEC = BuilderCodec.builder(DisplayBlock.class, DisplayBlock::new)
        .append(new KeyedCodec<>("Kind", Codec.STRING), (v,s)->v.kind=s, v->v.kind).add()
        .append(new KeyedCodec<>("Style", Codec.STRING), (v,s)->v.style=s, v->v.style).add().build();
    private String kind = "Stand";
    private String style = "Wood";
    final List<Ref<EntityStore>> visuals = new ArrayList<>();
    SimpleItemContainer configured;
    ItemStack[] snapshot;
    int rotation = -1;
    float elapsed;
    boolean queued;
    boolean failed;
    public DisplayBlock() {}
    public DisplayBlock(String kind, String style) {
        DisplayRules.capacity(kind);
        this.kind = kind;
        this.style = style;
    }
    public String kind() { return kind; }
    public String style() { return style; }
    /** Call on the owning world thread; references are visual-only entities. */
    public List<Ref<EntityStore>> visualReferences() { return List.copyOf(visuals); }
    @Override public Component<ChunkStore> clone() { return new DisplayBlock(kind, style); }
}
