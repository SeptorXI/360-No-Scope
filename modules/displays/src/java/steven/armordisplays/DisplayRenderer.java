package steven.armordisplays;

import com.hypixel.hytale.component.*;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.asset.type.blocktype.config.BlockType;
import com.hypixel.hytale.server.core.asset.type.blocktype.config.RotationTuple;
import com.hypixel.hytale.server.core.asset.type.model.config.Model;
import com.hypixel.hytale.server.core.asset.type.model.config.ModelAsset;
import com.hypixel.hytale.server.core.entity.UUIDComponent;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.SimpleItemContainer;
import com.hypixel.hytale.server.core.modules.block.BlockModule;
import com.hypixel.hytale.server.core.modules.block.components.ItemContainerBlock;
import com.hypixel.hytale.server.core.modules.entity.component.*;
import com.hypixel.hytale.server.core.modules.entity.tracker.NetworkId;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.chunk.section.BlockSection;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import org.joml.Vector3d;
import org.joml.Vector3i;

public final class DisplayRenderer {
    private DisplayRenderer() {}
    public static void configure(DisplayBlock display, ItemContainerBlock storage) {
        SimpleItemContainer inventory=storage.getItemContainer();
        if (inventory!=null && inventory!=display.configured) {
            DisplayRules.configure(display.kind(),inventory);
            display.configured=inventory;
            display.snapshot=null;
        }
    }
    /** Owning world thread only. Never changes an authoritative item slot. */
    public static void reconcile(World world, Ref<ChunkStore> source) {
        if(source==null || !source.isValid()) return;
        Store<ChunkStore> chunks=world.getChunkStore().getStore();
        DisplayBlock display=chunks.getComponent(source,ArmorDisplaysPlugin.displayComponentType());
        ItemContainerBlock storage=chunks.getComponent(source,ItemContainerBlock.getComponentType());
        BlockModule.BlockStateInfo info=chunks.getComponent(source,BlockModule.BlockStateInfo.getComponentType());
        if(display==null || storage==null || info==null) return;
        configure(display,storage);
        Vector3i position=new Vector3i();
        if(!info.fillWorldPos(chunks,position) || info.getSectionRef()==null || !info.getSectionRef().isValid()) return;
        BlockSection section=chunks.getComponent(info.getSectionRef(),BlockSection.getComponentType());
        if(section==null || storage.getItemContainer()==null) return;
        String expected="AD_"+switch(display.kind()) { case "Stand"->"Armor_Stand_";case "Holder"->"Wall_Holder_";case "Rack"->"Wall_Rack_";default->throw new IllegalArgumentException("Display kind"); }+display.style();
        BlockType actual=BlockType.getAssetMap().getAsset(section.get(info.getIndex()));
        if(actual==null || !expected.equals(actual.getId())) { clear(world,display);return; }
        int rotationIndex=section.getRotationIndex(info.getIndex());
        ItemStack[] snapshot=new ItemStack[DisplayRules.capacity(display.kind())];
        for(short slot=0;slot<snapshot.length;slot++) snapshot[slot]=storage.getItemContainer().getItemStack(slot);
        boolean valid=display.visuals.stream().allMatch(Ref::isValid);
        if(valid && display.rotation==rotationIndex && Arrays.equals(snapshot,display.snapshot)) return;
        RotationTuple rotation=RotationTuple.get(rotationIndex);
        List<Holder<EntityStore>> prepared=new ArrayList<>();
        if("Stand".equals(display.kind())) {
            boolean any=false;
            for(int i=0;i<snapshot.length;i++) any|=DisplayRules.accepts(display.kind(),i,snapshot[i]);
            if(any) prepared.add(stand(world,source,position,rotation,snapshot));
        } else {
            ItemLayout.Placement[] layouts=new ItemLayout.Placement[snapshot.length];
            for(int slot=0;slot<snapshot.length;slot++) {
                if(!DisplayRules.accepts(display.kind(),slot,snapshot[slot])) continue;
                try {
                    layouts[slot]=ItemLayout.placement(snapshot[slot].getItem(),display.kind());
                    // A pending model is omitted until ready; other slots still update.
                    // Keep this snapshot different from its source so it retries.
                    if(layouts[slot]==null) snapshot[slot]=null;
                } catch(RuntimeException failure) {
                    ArmorDisplaysPlugin.report("Cannot render stored weapon "+snapshot[slot].getItemId()+" (item retained)",failure);
                }
            }
            // Avoid rebuilding already-correct props while another model is loading.
            if(valid && display.rotation==rotationIndex && Arrays.equals(snapshot,display.snapshot)) return;
            for(int slot=0;slot<snapshot.length;slot++) {
                ItemLayout.Placement layout=layouts[slot];
                if(layout==null) continue;
                double y="Holder".equals(display.kind())?12:12+18*slot;
                double z="Holder".equals(display.kind())?8:7;
                // Furniture R-Attachment (-16,0,0) at 32px/block, before block rotation.
                Vector3d center=new Vector3d(-0.5,y/32,z/32);
                Vector3d offset=new Vector3d(layout.center());
                center.sub(offset);
                rotation.applyRotationTo(center);
                center.add(position.x+0.5,position.y,position.z+0.5);
                Rotation3f pose=new Rotation3f(layout.rotation());
                rotation.applyRotationTo(pose);
                prepared.add(base(world,source,layout.model(),center,pose));
            }
        }
        clear(world,display);
        Store<EntityStore> entities=world.getEntityStore().getStore();
        try {
            for(Holder<EntityStore> holder:prepared) display.visuals.add(entities.addEntity(holder,AddReason.SPAWN));
            display.snapshot=snapshot;
            display.rotation=rotationIndex;
            display.failed=false;
        } catch(RuntimeException failure) {
            clear(world,display);
            throw failure;
        }
    }
    private static Holder<EntityStore> stand(World world,Ref<ChunkStore> source,Vector3i position,RotationTuple rotation,ItemStack[] saved) {
        ModelAsset asset=ModelAsset.getAssetMap().getAsset("AD_Equipment_Mannequin");
        if(asset==null) throw new IllegalStateException("Missing AD_Equipment_Mannequin model asset");
        Vector3d center=new Vector3d(-0.5,4.0/32,0);
        rotation.applyRotationTo(center);
        center.add(position.x+0.5,position.y,position.z+0.5);
        // Native Player/Mannequin face +Z; the furniture's presentation front is -Z.
        Rotation3f pose=new Rotation3f(0,(float)Math.PI,0);rotation.applyRotationTo(pose);
        Holder<EntityStore> holder=base(world,source,Model.createUnitScaleModel(asset),center,pose);
        SimpleItemContainer armor=new SimpleItemContainer((short)4);
        for(short slot=0;slot<4;slot++) if(DisplayRules.accepts("Stand",slot,saved[slot]))
            armor.setItemStackForSlot(slot,DisplayRules.visualStack(saved[slot]));
        SimpleItemContainer main=new SimpleItemContainer((short)1),off=new SimpleItemContainer((short)1);
        if(DisplayRules.accepts("Stand",4,saved[4])) main.setItemStackForSlot((short)0,DisplayRules.visualStack(saved[4]));
        if(DisplayRules.accepts("Stand",5,saved[5])) off.setItemStackForSlot((short)0,DisplayRules.visualStack(saved[5]));
        holder.addComponent(InventoryComponent.Armor.getComponentType(),new InventoryComponent.Armor(armor));
        holder.addComponent(InventoryComponent.Hotbar.getComponentType(),new InventoryComponent.Hotbar(main,(byte)0));
        holder.addComponent(InventoryComponent.Utility.getComponentType(),new InventoryComponent.Utility(off,(byte)0));
        holder.addComponent(HeadRotation.getComponentType(),new HeadRotation(pose));
        return holder;
    }
    private static Holder<EntityStore> base(World world,Ref<ChunkStore> source,Model model,Vector3d position,Rotation3f rotation) {
        Holder<EntityStore> holder=EntityStore.REGISTRY.newHolder();
        holder.addComponent(EntityStore.REGISTRY.getNonSerializedComponentType(),NonSerialized.get());
        holder.addComponent(ArmorDisplaysPlugin.visualComponentType(),new VisualMarker(source));
        holder.addComponent(UUIDComponent.getComponentType(),UUIDComponent.randomUUID());
        holder.addComponent(NetworkId.getComponentType(),new NetworkId(world.getEntityStore().takeNextNetworkId()));
        holder.addComponent(TransformComponent.getComponentType(),new TransformComponent(position,rotation));
        holder.addComponent(ModelComponent.getComponentType(),new ModelComponent(model));
        holder.addComponent(Invulnerable.getComponentType(),Invulnerable.INSTANCE);
        return holder;
    }
    public static void clear(World world,DisplayBlock display) {
        Store<EntityStore> entities=world.getEntityStore().getStore();
        for(Ref<EntityStore> visual:List.copyOf(display.visuals)) {
            if(visual.isValid()) {
                emptyVisualInventory(visual,entities);
                entities.removeEntity(visual,RemoveReason.REMOVE);
            }
        }
        display.visuals.clear();display.snapshot=null;
    }
    static void emptyVisualInventory(Ref<EntityStore> visual,ComponentAccessor<EntityStore> entities) {
        // These are separate presentation containers, never the saved block container.
        InventoryComponent.Armor armor=entities.getComponent(visual,InventoryComponent.Armor.getComponentType());
        InventoryComponent.Hotbar hotbar=entities.getComponent(visual,InventoryComponent.Hotbar.getComponentType());
        InventoryComponent.Utility utility=entities.getComponent(visual,InventoryComponent.Utility.getComponentType());
        if(armor!=null) armor.getInventory().clear();
        if(hotbar!=null) hotbar.getInventory().clear();
        if(utility!=null) utility.getInventory().clear();
    }
}
