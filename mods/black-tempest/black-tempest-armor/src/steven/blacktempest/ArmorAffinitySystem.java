package steven.blacktempest;

import com.airijko.endlessleveling.api.EndlessLevelingAPI;
import com.airijko.endlessleveling.EndlessLeveling;
import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.protocol.ItemArmorSlot;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.UUIDComponent;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Consumer;

/** Owns only this addon's class filter, persisted return storage and leased attributes. */
public final class ArmorAffinitySystem extends EntityTickingSystem<EntityStore> implements AutoCloseable {
    private final EndlessLevelingAPI api = EndlessLevelingAPI.get();
    private final AffinityLedger ledger = new AffinityLedger(api::setExternalAttributeBonus);
    private record Binding(ItemContainer container, ArmorEquipGate gate) {}
    private final Map<UUID,Binding> gates = new HashMap<>();
    private final Map<UUID,Long> notifications = new ConcurrentHashMap<>();
    private final Map<UUID,String> failures = new HashMap<>();
    private final Consumer<String> errors;
    private final Map<UUID,Ref<EntityStore>> lastActors=new HashMap<>(),disconnectedActors=new HashMap<>();
    private boolean closed;
    public ArmorAffinitySystem() { this(System.err::println); }
    public ArmorAffinitySystem(Consumer<String> errors) { this.errors=Objects.requireNonNull(errors); }
    @Override public Query<EntityStore> getQuery() { return Player.getComponentType(); }
    @Override public boolean isParallel(int count, int size) { return false; }
    public boolean isPrimaryMage(UUID uuid) {
        String primary=api.getPrimaryClassId(uuid);
        return primary!=null && api.sharesClassPath(primary,"mage");
    }
    private void notify(UUID uuid, PlayerRef player, String message) {
        if(player==null)return;
        long now=System.currentTimeMillis();
        Long before=notifications.putIfAbsent(uuid,now);
        if(before!=null && now-before<5_000)return;
        notifications.put(uuid,now); player.sendMessage(Message.raw(message));
    }
    public synchronized void refresh(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor, long nowMs) {
        if(closed || ref==null || !ref.isValid() || accessor==null)return;
        var player=accessor.getComponent(ref,PlayerRef.getComponentType());
        var identity=accessor.getComponent(ref,UUIDComponent.getComponentType());
        UUID uuid=player!=null?player.getUuid():identity!=null?identity.getUuid():null;
        if(uuid==null)return;
        disconnectedActors.entrySet().removeIf(entry->!entry.getValue().isValid());
        var disconnected=disconnectedActors.get(uuid);
        if(disconnected==ref)return;
        if(disconnected!=null)disconnectedActors.remove(uuid);
        lastActors.put(uuid,ref);
        var actor=accessor.getComponent(ref,Player.getComponentType());
        var armor=accessor.getComponent(ref,InventoryComponent.Armor.getComponentType());
        var container=armor==null?null:armor.getInventory();
        boolean eligible=isPrimaryMage(uuid),filterReady=container==null,failed=false;
        try {
            Binding binding=gates.get(uuid);
            if(binding!=null && binding.container()!=container) { binding.gate().close(); gates.remove(uuid); binding=null; }
            if(container!=null) {
                if(binding==null) { binding=new Binding(container,new ArmorEquipGate());gates.put(uuid,binding); }
                binding.gate().bind(container,()->isPrimaryMage(uuid),message->notify(uuid,player,message));
            }
            filterReady=true;
        } catch(RuntimeException error) {
            String message=error.toString();
            if(!message.equals(failures.put(uuid,message)))errors.accept("Black Tempest equip restriction failed closed for "+uuid+": "+message);
            eligible=false;failed=true;
        }
        var pending=accessor.getComponent(ref,BlackTempestPlugin.returnComponentType());
        boolean invalidWorn=false;
        if(container!=null && (!eligible || !filterReady)) for(short slot=0;slot<container.getCapacity();slot++)
            if(ArmorEquipGate.isBlackTempest(container.getItemStack(slot)))invalidWorn=true;
        boolean changed=false;
        long initialRevision=pending==null?0:pending.revision();
        int initialPending=pending==null?0:pending.pending();
        try {
            if(invalidWorn) {
                if(pending==null) { pending=new ArmorReturnState();accessor.putComponent(ref,BlackTempestPlugin.returnComponentType(),pending); }
                changed=ArmorEquipGate.evacuate(container,pending)>0;
            }
            if(pending!=null && pending.pending()>0) {
                var storage=accessor.getComponent(ref,InventoryComponent.Storage.getComponentType());
                var hotbar=accessor.getComponent(ref,InventoryComponent.Hotbar.getComponentType());
                var backpack=accessor.getComponent(ref,InventoryComponent.Backpack.getComponentType());
                int returned=ArmorEquipGate.returnPending(pending,
                    storage==null?null:storage.getInventory(),hotbar==null?null:hotbar.getInventory(),backpack==null?null:backpack.getInventory());
                changed|=returned>0;
                if(pending.pending()>0)notify(uuid,player,"Unequipped Black Tempest pieces are stored safely; free inventory slots to receive them.");
                else if(invalidWorn)notify(uuid,player,"Black Tempest armor requires primary Mage. Your pieces were returned to inventory.");
            }
        } catch(RuntimeException error) {
            eligible=false;failed=true;
            String message="safe inventory return: "+error;
            if(!message.equals(failures.put(uuid,message)))errors.accept("Black Tempest return failed for "+uuid+"; existing stacks preserved: "+message);
        } finally {
            changed|=pending!=null && (pending.revision()!=initialRevision || pending.pending()!=initialPending);
            if(changed && actor!=null)actor.markNeedsSave();
        }
        if(!failed)failures.remove(uuid);
        boolean alive=accessor.getComponent(ref,DeathComponent.getComponentType())==null;
        var stats=accessor.getComponent(ref,EntityStatMap.getComponentType());
        var health=stats==null?null:stats.get(DefaultEntityStatTypes.getHealth());
        alive &= health==null || health.get()>health.getMin();
        if(ledger.refresh(uuid,alive,eligible && filterReady,snapshot(container),nowMs))recalculate(ref,accessor,uuid);
    }
    private void recalculate(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor, UUID uuid) {
        var plugin=EndlessLeveling.getInstance();
        var data=plugin==null?null:plugin.getPlayerDataManager().get(uuid);
        var skill=plugin==null?null:plugin.getSkillManager();
        if(data!=null && skill!=null) {
            skill.applyHealthModifiers(ref,accessor,data);
            skill.applyFlowModifiers(ref,accessor,data);
            skill.applyMovementSpeedModifier(ref,accessor,data);
        }
    }
    /** Shared pure/native fixture entry; native hard equip enforcement is ArmorEquipGate. */
    public synchronized boolean reconcile(UUID uuid, boolean alive, ItemContainer armor, long nowMs) {
        if(closed)return false;
        return ledger.refresh(uuid,alive,isPrimaryMage(uuid),snapshot(armor),nowMs);
    }
    public static EnumMap<AffinityRules.Slot,AffinityRules.Worn> snapshot(ItemContainer container) {
        var worn=new EnumMap<AffinityRules.Slot,AffinityRules.Worn>(AffinityRules.Slot.class);
        if(container!=null)for(var piece:AffinityRules.PIECES) {
            var slot=ItemArmorSlot.valueOf(piece.slot().name());short index=(short)slot.getValue();
            if(index<0 || index>=container.getCapacity())continue;
            var stack=container.getItemStack(index);
            if(stack==null || ItemStack.isEmpty(stack))continue;
            var armor=stack.getItem().getArmor();
            worn.put(piece.slot(),new AffinityRules.Worn(stack.getItemId(),stack.getQuantity(),stack.isBroken(),armor!=null && armor.getArmorSlot()==slot));
        }
        return worn;
    }
    @Override public void tick(float dt,int index,ArchetypeChunk<EntityStore> chunk,Store<EntityStore> store,CommandBuffer<EntityStore> buffer) {
        refresh(chunk.getReferenceTo(index),buffer,System.currentTimeMillis());
    }
    public synchronized void disconnect(UUID player) {
        var actor=lastActors.remove(player);if(actor!=null)disconnectedActors.put(player,actor);
        ledger.remove(player,System.currentTimeMillis());var binding=gates.remove(player);
        if(binding!=null)binding.gate().close();notifications.remove(player);failures.remove(player);
    }
    @Override public synchronized void close() { if(closed)return;closed=true;ledger.close();for(var binding:gates.values())binding.gate().close();gates.clear();notifications.clear();failures.clear();lastActors.clear();disconnectedActors.clear(); }
}
