package steven.armordisplays;

import com.hypixel.hytale.component.*;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.math.util.ChunkUtil;
import com.hypixel.hytale.server.core.asset.type.blockhitbox.BlockBoundingBoxes;
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
import com.hypixel.hytale.server.core.universe.world.SetBlockSettings;
import com.hypixel.hytale.server.core.universe.world.chunk.BlockOperations;
import com.hypixel.hytale.server.core.universe.world.chunk.heightmap.HeightmapColumn;
import com.hypixel.hytale.server.core.universe.world.chunk.section.BlockComponentSection;
import com.hypixel.hytale.server.core.universe.world.chunk.section.BlockSection;
import com.hypixel.hytale.server.core.universe.world.chunk.section.ChunkSection;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.FillerBlockUtil;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.joml.Vector3d;
import org.joml.Vector3i;

public final class DisplayRenderer {
    private static final double RACK_SLOT_SPACING = 18.0 / 32;

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
        if("Stand".equals(display.kind()) && !display.footprintNormalized && section.getFiller(info.getIndex())==0)
            display.footprintNormalized=normalizeStandFootprint(world,chunks,position,actual,section.get(info.getIndex()),rotationIndex);
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
            boolean rack = "Rack".equals(display.kind());
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
                // Furniture R-Attachment (-16,0,0) at 32px/block, before block rotation.
                // Viewed from the front (-Z), slots run from +X to -X.
                Vector3d center = rack
                    ? new Vector3d(-0.5 + (1 - slot) * RACK_SLOT_SPACING, 30.0 / 32, 5.0 / 32 - layout.halfDepth())
                    : new Vector3d(-0.5, 12.0 / 32, 8.0 / 32);
                center.sub(layout.center());
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

    /** Remove only legacy stand fillers whose native origin still proves ownership of this root. */
    private static boolean normalizeStandFootprint(World world,Store<ChunkStore> chunks,Vector3i root,BlockType type,int blockId,int rotationIndex) {
        if(!"AD_Armor_Stand_Wood".equals(type.getId()) && !"AD_Armor_Stand_Metal".equals(type.getId())) return false;
        BlockBoundingBoxes hitbox=BlockBoundingBoxes.getAssetMap().getAsset(type.getHitboxTypeIndex());
        if(hitbox==null) return false;
        Set<Integer> retained=new HashSet<>();
        retained.add(FillerBlockUtil.pack(0,0,0));
        FillerBlockUtil.forEachFillerBlock(hitbox.get(rotationIndex),(x,y,z)->retained.add(FillerBlockUtil.pack(x,y,z)));
        List<Ref<ChunkStore>> refs=new ArrayList<>(18);
        List<BlockSection> sections=new ArrayList<>(18);
        List<BlockComponentSection> components=new ArrayList<>(18);
        // Old horizontal rotations fit this bounded union. Never load neighboring terrain.
        // Preflight every section before making the first change; a later refresh retries missing ones.
        for(int dx=-1;dx<=1;dx++) for(int dy=0;dy<=1;dy++) for(int dz=-1;dz<=1;dz++) {
            Ref<ChunkStore> ref=world.getChunkStore().getChunkSectionReferenceAtBlock(root.x+dx,root.y+dy,root.z+dz);
            if(ref==null || !ref.isValid()) return false;
            BlockSection section=chunks.getComponent(ref,BlockSection.getComponentType());
            ChunkSection chunk=chunks.getComponent(ref,ChunkSection.getComponentType());
            if(section==null || chunk==null || chunk.getChunkColumnReference()==null || !chunk.getChunkColumnReference().isValid()
                || chunks.getComponent(chunk.getChunkColumnReference(),HeightmapColumn.getComponentType())==null) return false;
            refs.add(ref);sections.add(section);
            components.add(chunks.getComponent(ref,BlockComponentSection.getComponentType()));
        }
        int flags=SetBlockSettings.NO_UPDATE_STATE|SetBlockSettings.NO_BREAK_FILLER|SetBlockSettings.NO_SET_FILLER
            |SetBlockSettings.NO_SEND_PARTICLES|SetBlockSettings.NO_SEND_AUDIO|SetBlockSettings.NO_DROP_ITEMS|SetBlockSettings.NO_FIRE_ON_BREAK;
        int i=0;
        for(int dx=-1;dx<=1;dx++) for(int dy=0;dy<=1;dy++) for(int dz=-1;dz<=1;dz++,i++) {
            if(retained.contains(FillerBlockUtil.pack(dx,dy,dz))) continue;
            int x=root.x+dx,y=root.y+dy,z=root.z+dz;
            BlockSection section=sections.get(i);
            int filler=section.getFiller(x,y,z);
            if(filler==0 || section.get(x,y,z)!=blockId || section.getRotationIndex(x,y,z)!=rotationIndex
                || FillerBlockUtil.unpackX(filler)!=dx || FillerBlockUtil.unpackY(filler)!=dy || FillerBlockUtil.unpackZ(filler)!=dz) continue;
            BlockComponentSection component=components.get(i);
            int index=ChunkUtil.indexBlock(x,y,z);
            if(component!=null && (component.getBlockReference(index)!=null || component.getBlockHolder(index)!=null)) continue;
            // NO_BREAK_FILLER prevents the native setter from following this filler back to the real root.
            if(!BlockOperations.setBlock(world.getChunkStore(),refs.get(i),x,y,z,0,BlockType.EMPTY,0,0,flags)
                || section.get(x,y,z)!=0 || section.getFiller(x,y,z)!=0) return false;
        }
        return true;
    }
    private static Holder<EntityStore> stand(World world,Ref<ChunkStore> source,Vector3i position,RotationTuple rotation,ItemStack[] saved) {
        ModelAsset asset=ModelAsset.getAssetMap().getAsset("AD_Equipment_Mannequin");
        if(asset==null) throw new IllegalStateException("Missing AD_Equipment_Mannequin model asset");
        Vector3d center=new Vector3d(0,4.0/32,0);
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
        holder.addComponent(Intangible.getComponentType(),Intangible.INSTANCE);
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
