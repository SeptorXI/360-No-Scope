package steven.blacktempest;

import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.Component;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.SimpleItemContainer;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/** Player-persisted safe return storage. Never drops or deletes class-invalid equipment. */
// Safe-return mechanics adapted from the workspace Crimson Brotherhood runtime; no art or item assets are reused.
public final class ArmorReturnState implements Component<EntityStore> {
    public static final BuilderCodec<ArmorReturnState> CODEC = BuilderCodec.builder(ArmorReturnState.class, ArmorReturnState::new)
        .append(new KeyedCodec<>("Container", SimpleItemContainer.CODEC), (state,value)->state.inventory=value, state->state.inventory).add()
        .build();
    private long revision;
    public long revision() { return revision; }
    public void changed() { revision++; }
    private SimpleItemContainer inventory = new SimpleItemContainer((short)4);
    public SimpleItemContainer inventory() { return inventory; }
    public int pending() { return inventory.countItemStacks(stack -> stack != null && !ItemStack.isEmpty(stack)); }
    public void ensureRoom(ItemStack incoming) {
        if (inventory.canAddItemStack(incoming)) return;
        int capacity = inventory.getCapacity();
        if (capacity > Short.MAX_VALUE - 4) throw new IllegalStateException("BlackTempest return storage capacity exhausted; equipped item preserved");
        var expanded = new SimpleItemContainer((short)(capacity + 4));
        for (short slot = 0; slot < capacity; slot++) {
            var stack = inventory.getItemStack(slot);
            if (stack != null && !ItemStack.isEmpty(stack) && !expanded.setItemStackForSlot(slot,stack).succeeded())
                throw new IllegalStateException("Cannot expand BlackTempest return storage; original container preserved");
        }
        inventory = expanded;changed();
    }
    @Override public ArmorReturnState clone() { var copy = new ArmorReturnState(); copy.inventory = inventory.clone();copy.revision=revision; return copy; }
}
