package steven.abtt;

import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.dependency.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.ItemArmorSlot;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.inventory.*;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.modules.interaction.Interactions;
import com.hypixel.hytale.server.core.modules.interaction.system.InteractionSystems;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/** A local player override; the shared Empty/unarmed asset is never changed. */
public final class ArmorCastingSystem extends EntityTickingSystem<EntityStore> {
    public static final String ROOT_ID="Root_ABTT_Channel";
    public static final String STORM_ROOT_ID="Root_ABTT_Storm";
    public static final InteractionType STORM_INPUT=InteractionType.Ability1;
    public static final short HANDS_SLOT=(short)ItemArmorSlot.Hands.getValue();
    public record Equipment(ItemContainer container,short slot,ItemStack stack){}
    private record Previous(Interactions component,String primary){}
    private static final Map<InteractionType,String> ROOTS=Map.of(InteractionType.Primary,ROOT_ID,STORM_INPUT,STORM_ROOT_ID);
    private final Map<Ref<EntityStore>,Map<InteractionType,Previous>> overrides=new ConcurrentHashMap<>();
    private final Map<Ref<EntityStore>,Set<InteractionType>> displaced=new ConcurrentHashMap<>();
    @Override public Query<EntityStore> getQuery(){return Player.getComponentType();}
    @Override public boolean isParallel(int count,int size){return false;}
    @Override public Set<Dependency<EntityStore>> getDependencies(){return Set.of(
        new SystemDependency<>(Order.BEFORE,InteractionSystems.TickInteractionManagerSystem.class),
        new SystemDependency<>(Order.BEFORE,InteractionSystems.TrackerTickSystem.class));}
    public static boolean empty(ItemStack stack){return stack==null||ItemStack.isEmpty(stack);}
    /** This is the actual worn slot, never a search of storage or hotbar. */
    public static Equipment equipped(Ref<EntityStore> ref,ComponentAccessor<EntityStore> accessor){
        if(ref==null||!ref.isValid()||accessor==null)return null;
        var armor=accessor.getComponent(ref,InventoryComponent.Armor.getComponentType());
        if(armor==null||armor.getInventory()==null||armor.getInventory().getCapacity()<=HANDS_SLOT)return null;
        var stack=armor.getInventory().getItemStack(HANDS_SLOT);
        return stack!=null&&stack.getQuantity()==1&&!stack.isBroken()&&ChannelRules.ITEM_ID.equals(stack.getItemId())
            ?new Equipment(armor.getInventory(),HANDS_SLOT,stack):null;
    }
    public static boolean eligible(Ref<EntityStore> ref,ComponentAccessor<EntityStore> accessor){
        if(equipped(ref,accessor)==null||accessor.getComponent(ref,DeathComponent.getComponentType())!=null)return false;
        var stats=accessor.getComponent(ref,EntityStatMap.getComponentType());
        var health=stats==null?null:stats.get(DefaultEntityStatTypes.getHealth());
        if(health!=null&&health.get()<=health.getMin())return false;
        // Native main-hand selection includes the Tool-mode override, not only the hotbar.
        if(!empty(InventoryComponent.getItemInHand(accessor,ref)))return false;
        var utility=accessor.getComponent(ref,InventoryComponent.Utility.getComponentType());
        return utility==null||empty(utility.getActiveItem());
    }
    /** Public so the isolated native fixture can exercise the exact dispatcher. */
    public boolean refresh(Ref<EntityStore> ref,ComponentAccessor<EntityStore> accessor){
        boolean ready=eligible(ref,accessor);
        var current=accessor.getComponent(ref,Interactions.getComponentType());
        var previous=overrides.computeIfAbsent(ref,key->new EnumMap<>(InteractionType.class));
        var yielded=displaced.computeIfAbsent(ref,key->EnumSet.noneOf(InteractionType.class));
        if(ready){
            if(current==null)current=accessor.ensureAndGetComponent(ref,Interactions.getComponentType());
            if(current==null)return false;
            for(var entry:ROOTS.entrySet()){
                var key=entry.getKey();var root=entry.getValue();var saved=previous.get(key);
                String actual=current.getInteractionId(key);
                boolean knownMmo=key==STORM_INPUT&&"MMO_Trigger_Ability1".equals(actual);
                if(saved!=null&&(current!=saved.component()||!root.equals(actual))){
                    if(knownMmo){previous.put(key,new Previous(current,actual));yielded.remove(key);}
                    else{previous.remove(key);yielded.add(key);continue;}
                }
                if(yielded.contains(key))continue;
                if(!previous.containsKey(key))previous.put(key,new Previous(current,root.equals(actual)?null:actual));
                if(!root.equals(actual))current.setInteractionId(key,root);
            }
        }else{
            displaced.remove(ref);
            for(var entry:ROOTS.entrySet()){
                var saved=previous.get(entry.getKey());
                if(saved!=null)restore(current,entry.getKey(),entry.getValue(),saved);
                else if(current!=null&&entry.getValue().equals(current.getInteractionId(entry.getKey())))current.removeInteractionId(entry.getKey());
            }
            overrides.remove(ref);
        }
        boolean primary=ready&&current!=null&&ROOT_ID.equals(current.getInteractionId(InteractionType.Primary));
        boolean storm=ready&&current!=null&&STORM_ROOT_ID.equals(current.getInteractionId(STORM_INPUT));
        ChannelInteraction.cleanup(ref,accessor,primary);
        if(!storm&&StormSystem.getComponentType()!=null)StormSystem.cancel(ref,accessor);
        return primary;
    }
    private static void restore(Interactions current,InteractionType key,String root,Previous previous){
        if(current!=previous.component()||!root.equals(current.getInteractionId(key)))return;
        if(previous.primary()==null)current.removeInteractionId(key);
        else current.setInteractionId(key,previous.primary());
    }
    @Override public void tick(float dt,int index,ArchetypeChunk<EntityStore> chunk,Store<EntityStore> store,CommandBuffer<EntityStore> buffer){
        refresh(chunk.getReferenceTo(index),buffer);
        overrides.keySet().removeIf(ref->!ref.isValid());
        displaced.keySet().removeIf(ref->!ref.isValid());
    }
    public void close(){
        for(var entry:overrides.entrySet()){
            var ref=entry.getKey();if(!ref.isValid())continue;
            var world=ref.getStore().getExternalData().getWorld();
            world.execute(()->{if(ref.isValid())for(var saved:entry.getValue().entrySet())
                restore(ref.getStore().getComponent(ref,Interactions.getComponentType()),saved.getKey(),ROOTS.get(saved.getKey()),saved.getValue());});
        }
        overrides.clear();
        displaced.clear();
    }
}
