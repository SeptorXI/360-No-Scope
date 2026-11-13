package steven.abtt;

import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.*;
import com.hypixel.hytale.protocol.InteractionState;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.InteractionItemChangeBehavior;
import com.hypixel.hytale.protocol.SoundCategory;
import com.hypixel.hytale.protocol.BlockMaterial;
import com.hypixel.hytale.protocol.AnimationSlot;
import com.hypixel.hytale.server.core.entity.AnimationUtils;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.asset.type.soundevent.config.SoundEvent;
import com.hypixel.hytale.server.core.asset.type.blocktype.config.BlockType;
import com.hypixel.hytale.server.core.inventory.*;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.meta.MetaKey;
import com.hypixel.hytale.server.core.modules.entity.component.*;
import com.hypixel.hytale.server.core.modules.entity.damage.*;
import com.hypixel.hytale.server.core.modules.entitystats.*;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.InteractionModule;
import com.hypixel.hytale.server.core.modules.interaction.Interactions;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.client.ChargingInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.*;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.TargetUtil;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.ziggfreed.mmoskilltree.ability.damage.AbilityDamageOrigin;
import com.ziggfreed.mmoskilltree.skill.SkillRegistry;
import org.joml.Vector3d;
import org.joml.Vector4d;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/** Native empty-hand input with authoritative worn-armor costs and bounded pulses. */
public final class ChannelInteraction extends ChargingInteraction {
    public static final BuilderCodec<ChannelInteraction> CODEC=BuilderCodec.builder(ChannelInteraction.class,ChannelInteraction::new,ChargingInteraction.CODEC).build();
    private static final MetaKey<Session> SESSION=Interaction.META_REGISTRY.registerMetaObject();
    private static final Map<UUID,Long> START_AUDIO=new ConcurrentHashMap<>();
    private static final Map<Ref<EntityStore>,Session> CASTING=new ConcurrentHashMap<>();
    private static final AbilityDamageOrigin.Payload ORIGIN=new AbilityDamageOrigin.Payload(List.of("MAGIC","UNARMED"),List.of(),"ABTT_Lightning",true,0);
    public static final class Session {
        public float nextPulse;
        public float lastContact=-100;
        public int acceptedPulses;
        public boolean started,stopped;
        public Ref<EntityStore> target;
        public ItemStack expected;
        public ItemContainer armorContainer;
        public short armorSlot;
        public Vector3d lastOrigin;
        public final FingertipBeams.State beams=new FingertipBeams.State();
        public void loseContact(){target=null;acceptedPulses=0;lastContact=-100;}
        public int contact(Ref<EntityStore> value,float time){
            if(!Objects.equals(target,value)||time-lastContact>ChannelRules.INTERVAL+0.12f)acceptedPulses=0;
            target=value;lastContact=time;return ++acceptedPulses;
        }
    }
    public record RayHit(Ref<EntityStore> target,Vector3d point,double distance){}
    public ChannelInteraction(){displayProgress=false;allowIndefiniteHold=true;cancelOnOtherClick=true;onItemChangeBehavior=InteractionItemChangeBehavior.Ignore;}
    @Override protected void simulateTick0(boolean first,float time,InteractionType type,InteractionContext c,CooldownHandler cd){super.simulateTick0(first,time,type,c,cd);}
    @Override protected void tick0(boolean first,float time,InteractionType type,InteractionContext c,CooldownHandler cd){
        Session s=c.getInstanceStore().getIfPresentMetaObject(SESSION);
        if(s==null){s=new Session();c.getInstanceStore().putMetaObject(SESSION,s);}
        try {
            if(type!=InteractionType.Primary||!Float.isFinite(time)||time<0||!validWorn(c,s)){stop(c,s,true);return;}
            super.tick0(first,time,type,c,cd);
            if(c.getState().state!=InteractionState.NotFinished){stop(c,s,false);return;}
            if(time+1e-5f<s.nextPulse){if(s.started)refreshBeams(c,s);return;}
            s.nextPulse=time+ChannelRules.INTERVAL; // Never burst-catch-up after a lag spike.
            if(!pulse(c,s,time))stop(c,s,true);
        }catch(RuntimeException rejected){
            stop(c,s,true);
            ABTickleTimePlugin.report(rejected);
        }
    }
    private static boolean validWorn(InteractionContext c,Session s){
        var b=c.getCommandBuffer();var owner=c.getOwningEntity();
        if(s.stopped||b==null||!ArmorCastingSystem.eligible(owner,b)||!ArmorCastingSystem.empty(c.getHeldItem()))return false;
        var overrides=b.getComponent(owner,Interactions.getComponentType());
        if(overrides==null||!ArmorCastingSystem.ROOT_ID.equals(overrides.getInteractionId(InteractionType.Primary)))return false;
        var worn=ArmorCastingSystem.equipped(owner,b);
        if(s.armorContainer!=null&&s.armorContainer!=worn.container())return false;
        // Native armor hit wear and Durability refunds may change durability between ticks.
        // All item identity/quantity/enchantment metadata and maximum durability must still match.
        if(s.expected!=null&&!sameWornItem(s.expected,worn.stack()))return false;
        s.armorContainer=worn.container();s.armorSlot=worn.slot();s.expected=worn.stack();return true;
    }
    public static boolean sameWornItem(ItemStack expected,ItemStack actual){
        return expected!=null&&actual!=null&&Double.compare(expected.getMaxDurability(),actual.getMaxDurability())==0&&
            actual.withDurability(expected.getDurability()).equals(expected);
    }
    /** Both debits happen on the owning world thread; any rejection restores the original values and item. */
    public static ItemStack pay(EntityStatMap stats,ItemContainer container,short slot,ItemStack before){
        return pay(stats,container,slot,before,ChannelRules.MANA,ChannelRules.STAMINA,ChannelRules.DURABILITY);
    }
    public static ItemStack pay(EntityStatMap stats,ItemContainer container,short slot,ItemStack before,float manaCost,float staminaCost,double durabilityCost){
        if(!Float.isFinite(manaCost)||!Float.isFinite(staminaCost)||!Double.isFinite(durabilityCost)||manaCost<0||staminaCost<0||durabilityCost<0)return null;
        if(stats==null||container==null||before==null||before.isBroken()||before.getQuantity()!=1||
           !Double.isFinite(before.getDurability())||!ChannelRules.ITEM_ID.equals(before.getItemId()))return null;
        int mana=DefaultEntityStatTypes.getMana(),stamina=DefaultEntityStatTypes.getStamina();
        var m=stats.get(mana);var st=stats.get(stamina);
        if(m==null||st==null||stats.isStatChangeSuppressed(mana,StatChangeDirection.LOWER)||stats.isStatChangeSuppressed(stamina,StatChangeDirection.LOWER)||
           !Float.isFinite(m.get())||!Float.isFinite(st.get())||!Float.isFinite(m.getMin())||!Float.isFinite(st.getMin())||m.get()-manaCost<Math.max(0,m.getMin())||
           st.get()-staminaCost<Math.max(0,st.getMin())||!Objects.equals(container.getItemStack(slot),before))return null;
        float mBefore=m.get(),sBefore=st.get();
        // Emit ordinary raw wear. SimpleEnchantments' InventoryChangeEvent listener makes its
        // native probabilistic Durability refund; applying its multiplier here would double it.
        ItemStack after=before.isUnbreakable()?before:before.withDurability(Math.max(0,before.getDurability()-durabilityCost));
        if(!container.replaceItemStackInSlot(slot,before,after).succeeded())return null;
        try {
            stats.subtractStatValue(mana,manaCost);stats.subtractStatValue(stamina,staminaCost);
            if(Math.abs(m.get()-(mBefore-manaCost))>1e-4||Math.abs(st.get()-(sBefore-staminaCost))>1e-4)
                throw new IllegalStateException("Native stat debit was suppressed");
            return after;
        }catch(RuntimeException rejected){
            stats.setStatValue(mana,mBefore);stats.setStatValue(stamina,sBefore);
            if(!container.replaceItemStackInSlot(slot,after,before).succeeded())throw new IllegalStateException("Cannot rollback rejected channel debit",rejected);
            return null;
        }
    }
    /** Public for the isolated native fixture; it uses the same armor/empty-hand gate as tick0. */
    public static boolean pulse(InteractionContext c,Session s,float time){
        var b=c.getCommandBuffer();var owner=c.getOwningEntity();
        if(!validWorn(c,s))return false;
        var skills=SkillRegistry.getInstance();
        if(skills==null||!skills.isSkillAvailable("MAGIC")||!skills.isSkillAvailable("UNARMED"))return false;
        ItemStack paid=pay(b.getComponent(owner,EntityStatMap.getComponentType()),s.armorContainer,s.armorSlot,s.expected);
        if(paid==null)return false;
        s.expected=paid;
        if(paid.isBroken())return false;
        var look=TargetUtil.getLook(owner,b);var origin=new Vector3d(look.getPosition());var direction=new Vector3d(look.getDirection()).normalize();
        s.lastOrigin=origin;
        if(!s.started){
            s.started=true;
            var previous=CASTING.put(owner,s);
            if(previous!=null&&previous!=s)FingertipBeams.clear(owner,previous.beams,b);
            // Explicitly deliver the native action profile to the wearer and nearby viewers.
            AnimationUtils.playAnimation(owner,AnimationSlot.Action,"ABTT_Gauntlets_Player","Channel",true,b);
            playStart(owner,origin,b);
        }
        sound("SFX_ABTT_Fingertip_Electricity",origin,b);
        RayHit hit=trace(owner,origin,direction,b);
        FingertipBeams.update(owner,s.beams,origin,direction,hit.point(),b);
        ParticleUtil.spawnParticleEffect("ABTT_Impact",hit.point(),b);
        if(hit.target()==null||b.getComponent(hit.target(),NPCEntity.getComponentType())==null){s.loseContact();return true;}
        Damage damage=applyHit(owner,hit.target(),hit.point(),b);
        if(damage.isCancelled()||!Float.isFinite(damage.getAmount())||damage.getAmount()<=0){s.loseContact();return true;}
        int contact=s.contact(hit.target(),time);
        if(contact>=ChannelRules.SLOW_PULSES)addEffect(owner,hit.target(),"ABTT_Conductive",false,b);
        if(contact>=ChannelRules.SCORCH_PULSES)addEffect(owner,hit.target(),"ABTT_Overload_Burn",true,b);
        return true;
    }
    public static Damage applyHit(Ref<EntityStore> owner,Ref<EntityStore> target,Vector3d point,CommandBuffer<EntityStore> b){
        return applyAbilityHit(owner,target,point,ChannelRules.DAMAGE,InteractionType.Primary,ORIGIN,b);
    }
    public static Damage applyAbilityHit(Ref<EntityStore> owner,Ref<EntityStore> target,Vector3d point,float amount,InteractionType input,AbilityDamageOrigin.Payload origin,CommandBuffer<EntityStore> b){
        if(!Float.isFinite(amount)||amount<=0)throw new IllegalArgumentException("Invalid lightning damage");
        var cause=DamageCause.getAssetMap().getAsset(ChannelRules.CAUSE_ID);
        if(cause==null)throw new IllegalStateException("Native Lightning damage cause missing");
        var damage=new Damage(new Damage.EntitySource(owner),cause,amount);
        var worn=ArmorCastingSystem.equipped(owner,b);
        if(!ArmorCastingSystem.eligible(owner,b))throw new IllegalStateException("Lightning requires worn gauntlets and two empty hands");
        damage.putMetaObject(ArmorEnchantments.WORN_STACK,worn.stack());
        damage.putMetaObject(Damage.HIT_LOCATION,new Vector4d(point,1));
        damage.putMetaObject(Damage.INTERACTION_TYPE,input);
        if((input==InteractionType.Primary&&origin==ORIGIN)||
           (input==ArmorCastingSystem.STORM_INPUT&&origin==StormSystem.ORIGIN))HybridScalingSystem.mark(damage);
        AbilityDamageOrigin.runAs(origin,()->{HybridScalingSystem.apply(damage,b);DamageSystems.executeDamage(target,b,damage);});
        ArmorEnchantments.afterHit(owner,target,damage,b);
        return damage;
    }
    public static boolean blocksLightning(int id){
        if(id==0)return false;
        var type=BlockType.getAssetMap().getAsset(id);
        return type==null||type.getMaterial()==BlockMaterial.Solid;
    }
    /** Native solid-block ray plus nearest living AABB. Players block the beam but receive no damage. */
    public static RayHit trace(Ref<EntityStore> owner,Vector3d origin,Vector3d direction,CommandBuffer<EntityStore> b){
        double limit=ChannelRules.RANGE;
        var wall=TargetUtil.getTargetLocation(b.getExternalData().getWorld(),ChannelInteraction::blocksLightning,origin.x,origin.y,origin.z,direction.x,direction.y,direction.z,limit);
        if(wall!=null)limit=Math.min(limit,origin.distance(wall));
        Ref<EntityStore> closest=null;double distance=limit;
        for(var ref:TargetUtil.getAllEntitiesInSphere(origin,ChannelRules.RANGE+3,b)){
            if(ref==null||!ref.isValid()||ref.equals(owner))continue;
            if(b.getComponent(ref,NPCEntity.getComponentType())==null&&b.getComponent(ref,Player.getComponentType())==null)continue;
            var healthMap=b.getComponent(ref,EntityStatMap.getComponentType());
            var health=healthMap==null?null:healthMap.get(DefaultEntityStatTypes.getHealth());
            if(health==null||health.get()<=health.getMin()||b.getComponent(ref,DeathComponent.getComponentType())!=null)continue;
            var transform=b.getComponent(ref,TransformComponent.getComponentType());var bounds=b.getComponent(ref,BoundingBox.getComponentType());
            if(transform==null||bounds==null)continue;
            var p=transform.getPosition();var box=bounds.getBoundingBox();
            double entry=ChannelRules.rayBox(origin.x,origin.y,origin.z,direction.x,direction.y,direction.z,
                p.x+box.min.x,p.y+box.min.y,p.z+box.min.z,p.x+box.max.x,p.y+box.max.y,p.z+box.max.z,limit);
            if(entry<distance||(wall==null&&closest==null&&entry==distance)){distance=entry;closest=ref;}
        }
        return new RayHit(closest,new Vector3d(direction).mul(distance).add(origin),distance);
    }
    public static void addEffect(Ref<EntityStore> owner,Ref<EntityStore> target,String id,boolean onlyAbsent,CommandBuffer<EntityStore>b){
        if(!target.isValid()||b.getComponent(target,DeathComponent.getComponentType())!=null||b.getComponent(target,Player.getComponentType())!=null)return;
        var effect=EntityEffect.getAssetMap().getAsset(id);if(effect==null)throw new IllegalStateException("Missing "+id);
        var controller=b.ensureAndGetComponent(target,EffectControllerComponent.getComponentType());
        if(controller!=null&&(!onlyAbsent||!controller.hasEffect(effect)))controller.addEffect(target,effect,b,owner);
    }
    private static void refreshBeams(InteractionContext c,Session s){
        var b=c.getCommandBuffer();var owner=c.getOwningEntity();
        var look=TargetUtil.getLook(owner,b);
        var origin=new Vector3d(look.getPosition());var forward=new Vector3d(look.getDirection()).normalize();
        // Visual endpoint follows every active interaction tick, independently of paid damage pulses.
        var hit=trace(owner,origin,forward,b);
        FingertipBeams.update(owner,s.beams,origin,forward,hit.point(),b);
    }
    public static void playStart(Ref<EntityStore> owner,Vector3d p,CommandBuffer<EntityStore>b){
        var player=b.getComponent(owner,PlayerRef.getComponentType());if(player==null)return;
        long now=System.nanoTime();Long old=START_AUDIO.get(player.getUuid());
        if(old==null||now-old>=8_000_000_000L){START_AUDIO.put(player.getUuid(),now);sound("SFX_ABTT_Start",p,b);}
        if(START_AUDIO.size()>256)START_AUDIO.entrySet().removeIf(e->now-e.getValue()>60_000_000_000L);
    }
    public static void sound(String id,Vector3d p,CommandBuffer<EntityStore>b){
        int index=SoundEvent.getAssetMap().getIndex(id);if(index<0)throw new IllegalStateException("Missing "+id);
        SoundUtil.playSoundEvent3d(index,SoundCategory.SFX,p,b);
    }
    private static void stop(InteractionContext c,Session s,boolean failed){
        stopVisuals(c.getOwningEntity(),s,c.getCommandBuffer());
        s.loseContact();if(failed)c.getState().state=InteractionState.Failed;
    }
    private static void stopVisuals(Ref<EntityStore> owner,Session s,ComponentAccessor<EntityStore> accessor){
        FingertipBeams.clear(owner,s.beams,accessor);
        if(!s.stopped&&s.started&&owner!=null&&owner.isValid()&&accessor!=null){
            s.stopped=true;
            var current=CASTING.get(owner);
            boolean superseded=current!=null&&current!=s;
            var manager=accessor.getComponent(owner,InteractionModule.get().getInteractionManagerComponent());
            boolean otherAction=manager!=null&&manager.getChains().values().stream().anyMatch(chain->
                chain.getServerState()==InteractionState.NotFinished&&chain.getRootInteraction()!=null&&
                !ArmorCastingSystem.ROOT_ID.equals(chain.getRootInteraction().getId()));
            // Do not clear a new action's animation when it has already interrupted this cast.
            if(!superseded&&!otherAction)AnimationUtils.stopAnimation(owner,AnimationSlot.Action,true,accessor);
            if(s.lastOrigin!=null&&accessor instanceof CommandBuffer<EntityStore> buffer)sound("SFX_ABTT_Stop",s.lastOrigin,buffer);
        }
        if(owner!=null)CASTING.remove(owner,s);
    }
    /** Covers an externally interrupted chain even when its final interaction tick is skipped. */
    public static void cleanup(Ref<EntityStore> owner,ComponentAccessor<EntityStore> accessor,boolean eligible){
        var session=CASTING.get(owner);if(session==null)return;
        var manager=accessor.getComponent(owner,InteractionModule.get().getInteractionManagerComponent());
        boolean running=manager!=null&&manager.getChains().values().stream().anyMatch(chain->
            chain.getRootInteraction()!=null&&ArmorCastingSystem.ROOT_ID.equals(chain.getRootInteraction().getId()));
        if(!eligible||!running){stopVisuals(owner,session,accessor);session.loseContact();}
        CASTING.keySet().removeIf(ref->!ref.isValid());
    }
    public static void clearAudioGate(){
        for(var entry:List.copyOf(CASTING.entrySet())){
            var owner=entry.getKey();var session=entry.getValue();
            if(owner.isValid())owner.getStore().getExternalData().getWorld().execute(()->{
                if(owner.isValid())stopVisuals(owner,session,owner.getStore());
            });
        }
        START_AUDIO.clear();CASTING.clear();
    }
}
