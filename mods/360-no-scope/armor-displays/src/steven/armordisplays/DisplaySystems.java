package steven.armordisplays;

import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.dependency.Dependency;
import com.hypixel.hytale.component.dependency.Order;
import com.hypixel.hytale.component.dependency.SystemDependency;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.RefSystem;
import com.hypixel.hytale.component.system.RefChangeSystem;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.server.core.modules.block.BlockModule;
import com.hypixel.hytale.server.core.modules.block.components.ItemContainerBlock;
import com.hypixel.hytale.server.core.modules.block.system.ItemContainerSystems;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.util.Set;

final class DisplaySystems {
    private DisplaySystems() {}
    static Query<ChunkStore> query() { return Query.and(ArmorDisplaysPlugin.displayComponentType(),ItemContainerBlock.getComponentType()); }
    static void configure(Ref<ChunkStore> ref,Store<ChunkStore> store) {
        DisplayBlock display=store.getComponent(ref,ArmorDisplaysPlugin.displayComponentType());
        ItemContainerBlock storage=store.getComponent(ref,ItemContainerBlock.getComponentType());
        if(display!=null && storage!=null) {
            try {DisplayRenderer.configure(display,storage);}
            catch(RuntimeException failure) {ArmorDisplaysPlugin.report("Display container policy rejected",failure);}
        }
    }
    static final class Lifecycle extends RefSystem<ChunkStore> {
        @Override public Query<ChunkStore> getQuery() { return query(); }
        @Override public Set<Dependency<ChunkStore>> getDependencies() {
            return Set.of(new SystemDependency<>(Order.AFTER,ItemContainerSystems.OnAddedOrRemoved.class));
        }
        @Override public void onEntityAdded(Ref<ChunkStore> ref,AddReason reason,Store<ChunkStore> store,CommandBuffer<ChunkStore> command) {
            configure(ref,store);
        }
        @Override public void onEntityRemove(Ref<ChunkStore> ref,RemoveReason reason,Store<ChunkStore> store,CommandBuffer<ChunkStore> command) {
            DisplayBlock display=store.getComponent(ref,ArmorDisplaysPlugin.displayComponentType());
            if(display!=null) {
                World world=store.getExternalData().getWorld();
                world.execute(()->DisplayRenderer.clear(world,display));
            }
        }
    }
    static final class ContainerChange extends RefChangeSystem<ChunkStore,ItemContainerBlock> {
        @Override public Query<ChunkStore> getQuery() { return ArmorDisplaysPlugin.displayComponentType(); }
        @Override public ComponentType<ChunkStore,ItemContainerBlock> componentType() { return ItemContainerBlock.getComponentType(); }
        private void apply(Ref<ChunkStore> ref,ItemContainerBlock value,Store<ChunkStore> store) {
            DisplayBlock display=store.getComponent(ref,ArmorDisplaysPlugin.displayComponentType());
            if(display!=null && value!=null) DisplayRenderer.configure(display,value);
        }
        @Override public void onComponentAdded(Ref<ChunkStore> ref,ItemContainerBlock value,Store<ChunkStore> store,CommandBuffer<ChunkStore> command) { apply(ref,value,store); }
        @Override public void onComponentSet(Ref<ChunkStore> ref,ItemContainerBlock old,ItemContainerBlock value,Store<ChunkStore> store,CommandBuffer<ChunkStore> command) { apply(ref,value,store); }
        @Override public void onComponentRemoved(Ref<ChunkStore> ref,ItemContainerBlock value,Store<ChunkStore> store,CommandBuffer<ChunkStore> command) {}
    }
    static final class DisplayChange extends RefChangeSystem<ChunkStore,DisplayBlock> {
        @Override public Query<ChunkStore> getQuery() { return ItemContainerBlock.getComponentType(); }
        @Override public ComponentType<ChunkStore,DisplayBlock> componentType() { return ArmorDisplaysPlugin.displayComponentType(); }
        @Override public void onComponentAdded(Ref<ChunkStore> ref,DisplayBlock value,Store<ChunkStore> store,CommandBuffer<ChunkStore> command) {
            ItemContainerBlock storage=store.getComponent(ref,ItemContainerBlock.getComponentType());
            if(storage!=null) DisplayRenderer.configure(value,storage);
        }
        @Override public void onComponentSet(Ref<ChunkStore> ref,DisplayBlock old,DisplayBlock value,Store<ChunkStore> store,CommandBuffer<ChunkStore> command) {
            World world=store.getExternalData().getWorld();
            world.execute(()->DisplayRenderer.clear(world,old));
            onComponentAdded(ref,value,store,command);
        }
        @Override public void onComponentRemoved(Ref<ChunkStore> ref,DisplayBlock value,Store<ChunkStore> store,CommandBuffer<ChunkStore> command) {
            World world=store.getExternalData().getWorld();
            world.execute(()->DisplayRenderer.clear(world,value));
        }
    }
    static final class Refresh extends EntityTickingSystem<ChunkStore> {
        @Override public Query<ChunkStore> getQuery() { return Query.and(query(),BlockModule.BlockStateInfo.getComponentType()); }
        @Override public void tick(float dt,int index,ArchetypeChunk<ChunkStore> chunk,Store<ChunkStore> store,CommandBuffer<ChunkStore> command) {
            DisplayBlock display=chunk.getComponent(index,ArmorDisplaysPlugin.displayComponentType());
            display.elapsed+=dt;
            if(display.queued || display.elapsed<0.25f) return;
            display.elapsed=0;display.queued=true;
            Ref<ChunkStore> source=chunk.getReferenceTo(index);
            World world=store.getExternalData().getWorld();
            world.execute(()->{
                try {DisplayRenderer.reconcile(world,source);}
                catch(RuntimeException failure) {
                    if(!display.failed) ArmorDisplaysPlugin.report("Display visual refresh failed (saved items retained)",failure);
                    display.failed=true;
                } finally {display.queued=false;}
            });
        }
    }
    static final class OrphanCleanup extends EntityTickingSystem<EntityStore> {
        @Override public Query<EntityStore> getQuery() { return ArmorDisplaysPlugin.visualComponentType(); }
        @Override public void tick(float dt,int index,ArchetypeChunk<EntityStore> chunk,Store<EntityStore> store,CommandBuffer<EntityStore> command) {
            VisualMarker marker=chunk.getComponent(index,ArmorDisplaysPlugin.visualComponentType());
            Ref<ChunkStore> source=marker.source();
            if(source==null || !source.isValid() || store.getExternalData().getWorld().getChunkStore().getStore()
                .getComponent(source,ArmorDisplaysPlugin.displayComponentType())==null) {
                Ref<EntityStore> visual=chunk.getReferenceTo(index);
                DisplayRenderer.emptyVisualInventory(visual,command);
                command.removeEntity(visual,RemoveReason.REMOVE);
            }
        }
    }
}
