package steven.abtt;

import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.dependency.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.protocol.ColorLight;
import com.hypixel.hytale.server.core.asset.type.blocktype.config.BlockType;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.inventory.*;
import com.hypixel.hytale.server.core.modules.entity.component.*;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entity.system.EntitySystems;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/** One steady native environmental light per wearer. No particles, extra entities or persistent save state. */
public final class GauntletGlowSystem extends EntityTickingSystem<EntityStore> implements AutoCloseable {
    public static final byte RADIUS=2,RED=2,GREEN=1,BLUE=4;
    private final Object ownerToken=new Object();
    private final Set<Ref<EntityStore>> ownedRefs=ConcurrentHashMap.newKeySet();
    private volatile boolean closed;

    /** The subtype/token is the ownership marker; an unrelated identical-color light is never adopted. */
    public static final class OwnedLight extends DynamicLight {
        private final Object ownerToken;
        private boolean released;
        private OwnedLight(Object token,ColorLight color,boolean released){super(color);ownerToken=token;this.released=released;}
        @Override public Component<EntityStore> clone(){
            var color=getColorLight();
            return new OwnedLight(ownerToken,color==null?null:new ColorLight(color),released||!matches(color));
        }
    }
    public static ColorLight expectedLight(){return new ColorLight(RADIUS,RED,GREEN,BLUE);}
    private static boolean matches(ColorLight light){
        return light!=null&&light.radius==RADIUS&&light.red==RED&&light.green==GREEN&&light.blue==BLUE;
    }
    @Override public Query<EntityStore> getQuery(){return Player.getComponentType();}
    @Override public boolean isParallel(int count,int size){return false;}
    @Override public Set<Dependency<EntityStore>> getDependencies(){return Set.of(
        new SystemDependency<>(Order.BEFORE,EntitySystems.DynamicLightTracker.class));}
    @Override public void tick(float dt,int index,ArchetypeChunk<EntityStore> chunk,Store<EntityStore> store,CommandBuffer<EntityStore> buffer){
        refresh(chunk.getReferenceTo(index),buffer);
    }
    /** Unlike the attack gate, ordinary occupied hands do not suppress the worn armor's appearance. */
    public static boolean wornAlive(Ref<EntityStore> ref,ComponentAccessor<EntityStore> accessor){
        if(ref==null||!ref.isValid()||ArmorCastingSystem.equipped(ref,accessor)==null||
           accessor.getComponent(ref,DeathComponent.getComponentType())!=null)return false;
        var stats=accessor.getComponent(ref,EntityStatMap.getComponentType());
        var health=stats==null?null:stats.get(DefaultEntityStatTypes.getHealth());
        return health==null||Float.isFinite(health.get())&&health.get()>health.getMin();
    }
    /** Mirrors native ItemComponent.computeDynamicLight, including block-state torches. */
    public static ColorLight heldLight(ItemStack stack){
        if(ArmorCastingSystem.empty(stack))return null;
        var item=stack.getItem();if(item==null)return null;
        if(item.hasBlockType()){
            var block=BlockType.getAssetMap().getAsset(stack.getBlockKey());
            return block==null?null:block.getLight();
        }
        return item.getLight();
    }
    public static boolean hasHeldLight(Ref<EntityStore> ref,ComponentAccessor<EntityStore> accessor){
        if(heldLight(InventoryComponent.getItemInHand(accessor,ref))!=null)return true;
        var offhand=accessor.getComponent(ref,InventoryComponent.Utility.getComponentType());
        return offhand!=null&&heldLight(offhand.getActiveItem())!=null;
    }
    private boolean owned(DynamicLight light){
        if(!(light instanceof OwnedLight marker)||marker.ownerToken!=ownerToken||marker.released)return false;
        if(!matches(marker.getColorLight())){
            // A different writer claimed our component in place. Its color and component remain untouched.
            marker.released=true;return false;
        }
        return true;
    }
    public boolean owns(Ref<EntityStore> ref,ComponentAccessor<EntityStore> accessor){
        return ref!=null&&ref.isValid()&&owned(accessor.getComponent(ref,DynamicLight.getComponentType()));
    }
    private boolean wanted(Ref<EntityStore> ref,ComponentAccessor<EntityStore> accessor){
        return !closed&&wornAlive(ref,accessor)&&
            accessor.getComponent(ref,PersistentDynamicLight.getComponentType())==null&&!hasHeldLight(ref,accessor);
    }
    private void remember(Ref<EntityStore> ref){
        // Prune only on a newly owned reference, not on every steady-light tick.
        if(ownedRefs.add(ref))ownedRefs.removeIf(previous->!previous.isValid());
    }
    /**
     * Public native-fixture entry. Store access changes immediately. CommandBuffer transitions recheck
     * live ownership/equipment at commit; true means active or requested, not that a queued add has committed.
     */
    public boolean refresh(Ref<EntityStore> ref,ComponentAccessor<EntityStore> accessor){
        if(ref==null||!ref.isValid()||accessor==null)return false;
        var current=accessor.getComponent(ref,DynamicLight.getComponentType());
        boolean ours=owned(current),want=wanted(ref,accessor);
        if(ours&&want){remember(ref);return true;}
        if(!ours&&current!=null){ownedRefs.remove(ref);return false;}
        if(!ours&&!want){ownedRefs.remove(ref);return false;}
        if(accessor instanceof CommandBuffer<EntityStore> buffer){
            buffer.run(store->{if(ref.isValid()&&ref.getStore()==store)reconcile(ref,store);});
        }else reconcile(ref,accessor);
        return want;
    }
    private void reconcile(Ref<EntityStore> ref,ComponentAccessor<EntityStore> accessor){
        var current=accessor.getComponent(ref,DynamicLight.getComponentType());
        boolean ours=owned(current),want=wanted(ref,accessor);
        if(ours){
            if(want)remember(ref);
            else{accessor.tryRemoveComponent(ref,DynamicLight.getComponentType());ownedRefs.remove(ref);}
        }else if(current==null&&want){
            accessor.putComponent(ref,DynamicLight.getComponentType(),new OwnedLight(ownerToken,expectedLight(),false));
            remember(ref);
        }else ownedRefs.remove(ref);
    }
    private void removeOwned(Ref<EntityStore> ref,ComponentAccessor<EntityStore> accessor){
        if(owned(accessor.getComponent(ref,DynamicLight.getComponentType())))accessor.tryRemoveComponent(ref,DynamicLight.getComponentType());
    }
    @Override public void close(){
        closed=true;
        for(var ref:ownedRefs){
            if(!ref.isValid())continue;
            var world=ref.getStore().getExternalData().getWorld();
            world.execute(()->{if(ref.isValid())removeOwned(ref,ref.getStore());});
        }
        ownedRefs.clear();
    }
}
