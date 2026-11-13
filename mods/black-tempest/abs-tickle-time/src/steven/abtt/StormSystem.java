package steven.abtt;

import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.dependency.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.protocol.AnimationSlot;
import com.hypixel.hytale.server.core.entity.AnimationUtils;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.modules.entity.component.*;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.modules.interaction.Interactions;
import com.hypixel.hytale.server.core.modules.interaction.system.InteractionSystems;
import com.hypixel.hytale.server.core.universe.world.*;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.TargetUtil;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.ziggfreed.mmoskilltree.ability.damage.AbilityDamageOrigin;
import com.ziggfreed.mmoskilltree.skill.SkillRegistry;
import org.joml.Vector3d;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/** Only recent casters carry this ephemeral component; all effects and writes stay on their world thread. */
public final class StormSystem extends EntityTickingSystem<EntityStore> {
    public static final double AIM_RANGE=20,RADIUS=4,DURATION=3,INTERVAL=.5,DURABILITY=1;
    public static final int WAVES=6,MAX_TARGETS=24;
    public static final float DAMAGE=24,MANA=35,STAMINA=5,COOLDOWN=20;
    public static final String COOLDOWN_ID="ABTT_Storm";
    public static final AbilityDamageOrigin.Payload ORIGIN=new AbilityDamageOrigin.Payload(List.of("MAGIC","UNARMED"),List.of(),"ABTT_Storm",true,0);
    private static final double STORM_CLEARANCE=9;
    private static final int MAX_HIT_EFFECTS=4;
    private static ComponentType<EntityStore,State> componentType;
    private static final Map<Ref<EntityStore>,State> PENDING=new ConcurrentHashMap<>();
    static void initialize(ComponentType<EntityStore,State> type){componentType=type;}
    public static ComponentType<EntityStore,State> getComponentType(){return componentType;}
    /** CommandBuffer additions commit later; this also observes a just-accepted cast in the same tick. */
    public static State state(Ref<EntityStore> owner,ComponentAccessor<EntityStore> accessor){
        var committed=accessor.getComponent(owner,componentType);
        if(committed!=null){PENDING.remove(owner);return committed;}
        return PENDING.get(owner);
    }
    public static void close(){PENDING.clear();}
    public static final class State implements Component<EntityStore>{
        public double cooldownRemaining;
        public Session active;
        @Override public Component<EntityStore> clone(){var copy=new State();copy.cooldownRemaining=cooldownRemaining;return copy;}
    }
    public static final class Session{
        public Vector3d anchor;
        public double elapsed,nextWave;
        public int waves,lastTargets,totalHits;
        public final World world;
        public final ItemContainer armorContainer;
        public ItemStack expected;
        private Vector3d visualOrigin;
        private float visualScale;
        private final Map<Ref<EntityStore>,Integer> contacts=new HashMap<>();
        Session(Vector3d point,World world,ItemContainer armor,ItemStack item){anchor=new Vector3d(point);this.world=world;armorContainer=armor;expected=item;}
    }
    public record Aim(Vector3d point,Ref<EntityStore> entity,boolean block){}
    private record Victim(Ref<EntityStore> ref,Vector3d point,double distance){}
    @Override public Query<EntityStore> getQuery(){return componentType;}
    @Override public boolean isParallel(int count,int size){return false;}
    @Override public Set<Dependency<EntityStore>> getDependencies(){return Set.of(
        new SystemDependency<>(Order.AFTER,ArmorCastingSystem.class),
        new SystemDependency<>(Order.BEFORE,InteractionSystems.TickInteractionManagerSystem.class));}
    @Override public void tick(float dt,int index,ArchetypeChunk<EntityStore> chunk,Store<EntityStore> store,CommandBuffer<EntityStore> buffer){
        var ref=chunk.getReferenceTo(index);var state=chunk.getComponent(index,componentType);
        PENDING.remove(ref);
        try{advance(ref,state,dt,buffer);}catch(RuntimeException failure){state.active=null;ABTickleTimePlugin.report(failure);}
        if(state.active==null&&state.cooldownRemaining<=0)buffer.run(current->{
            if(ref.isValid()&&current.getComponent(ref,componentType)==state&&state.active==null&&state.cooldownRemaining<=0)
                current.tryRemoveComponent(ref,componentType);
        });
    }
    public static boolean cast(Ref<EntityStore> owner,Vector3d origin,Vector3d direction,CommandBuffer<EntityStore> buffer){
        if(owner==null||!owner.isValid()||buffer==null||owner.getStore()!=buffer.getStore()||!ArmorCastingSystem.eligible(owner,buffer))return false;
        var interactions=buffer.getComponent(owner,Interactions.getComponentType());
        if(interactions==null||!ArmorCastingSystem.STORM_ROOT_ID.equals(interactions.getInteractionId(ArmorCastingSystem.STORM_INPUT)))return false;
        var skills=SkillRegistry.getInstance();
        if(skills==null||!skills.isSkillAvailable("MAGIC")||!skills.isSkillAvailable("UNARMED"))return false;
        var state=state(owner,buffer);
        if(state!=null&&(state.active!=null||state.cooldownRemaining>0))return false;
        var aim=aim(owner,origin,direction,buffer);if(aim==null)return false;
        var equipment=ArmorCastingSystem.equipped(owner,buffer);
        if(!equipment.stack().isUnbreakable()&&equipment.stack().getDurability()<=DURABILITY)return false;
        var paid=ChannelInteraction.pay(buffer.getComponent(owner,EntityStatMap.getComponentType()),equipment.container(),equipment.slot(),equipment.stack(),MANA,STAMINA,DURABILITY);
        if(paid==null)return false;
        if(state==null){
            state=new State();PENDING.put(owner,state);buffer.putComponent(owner,componentType,state);
            PENDING.keySet().removeIf(ref->!ref.isValid());
        }
        // No fallible target or cost validation follows this commit.
        state.cooldownRemaining=COOLDOWN;
        state.active=new Session(aim.point(),buffer.getExternalData().getWorld(),equipment.container(),paid);
        AnimationUtils.playAnimation(owner,AnimationSlot.Action,"ABTT_Gauntlets_Player","Storm",true,buffer);
        ChannelInteraction.playStart(owner,state.active.anchor,buffer);
        wave(owner,state.active,buffer);
        return true;
    }
    /** Camera ray selects a living NPC or a solid surface. A player intercepts it without becoming a target. */
    public static Aim aim(Ref<EntityStore> owner,Vector3d origin,Vector3d direction,CommandBuffer<EntityStore> buffer){
        if(origin==null||direction==null||!finite(origin)||!finite(direction)||direction.lengthSquared()<1e-12)return null;
        var ray=new Vector3d(direction).normalize();
        var wall=TargetUtil.getTargetLocation(buffer.getExternalData().getWorld(),ChannelInteraction::blocksLightning,origin.x,origin.y,origin.z,ray.x,ray.y,ray.z,AIM_RANGE);
        // Native block DDA can report the next voxel past its requested range.
        // Such a hit must not create a fabricated surface anchor at the range boundary.
        if(wall!=null&&origin.distance(wall)>AIM_RANGE+1e-6)wall=null;
        double distance=wall==null?AIM_RANGE:Math.min(AIM_RANGE,origin.distance(wall));
        Ref<EntityStore> closest=null;
        for(var ref:TargetUtil.getAllEntitiesInSphere(origin,AIM_RANGE+3,buffer)){
            if(ref==null||!ref.isValid()||ref.equals(owner)||!living(ref,buffer))continue;
            if(buffer.getComponent(ref,NPCEntity.getComponentType())==null&&buffer.getComponent(ref,Player.getComponentType())==null)continue;
            var transform=buffer.getComponent(ref,TransformComponent.getComponentType());var bounds=buffer.getComponent(ref,BoundingBox.getComponentType());
            if(transform==null||bounds==null)continue;
            var p=transform.getPosition();var box=bounds.getBoundingBox();
            double entry=ChannelRules.rayBox(origin.x,origin.y,origin.z,ray.x,ray.y,ray.z,p.x+box.min.x,p.y+box.min.y,p.z+box.min.z,p.x+box.max.x,p.y+box.max.y,p.z+box.max.z,distance);
            if(entry<distance||(wall==null&&closest==null&&entry==distance)){closest=ref;distance=entry;}
        }
        if(closest!=null){
            if(buffer.getComponent(closest,Player.getComponentType())!=null)return null;
            return new Aim(new Vector3d(ray).mul(Math.max(0,distance-.05)).add(origin),closest,false);
        }
        return wall==null?null:new Aim(new Vector3d(ray).mul(Math.max(0,distance-.08)).add(origin),null,true);
    }
    public static void cancel(Ref<EntityStore> owner,ComponentAccessor<EntityStore> accessor){
        var state=state(owner,accessor);if(state!=null)state.active=null;
    }
    /** Public deterministic fixture entry: seconds of world time, with no burst catch-up after a stall. */
    public static void advance(Ref<EntityStore> owner,State state,float dt,CommandBuffer<EntityStore> buffer){
        if(state==null)return;
        if(!Float.isFinite(dt)||dt<0){state.active=null;return;}
        state.cooldownRemaining=Math.max(0,state.cooldownRemaining-dt);
        var active=state.active;if(active==null)return;
        if(owner==null||!owner.isValid()||buffer==null||owner.getStore()!=buffer.getStore()){
            state.active=null;return;
        }
        var worn=ArmorCastingSystem.equipped(owner,buffer);
        var inputs=buffer.getComponent(owner,Interactions.getComponentType());
        if(!ArmorCastingSystem.eligible(owner,buffer)||active.world!=buffer.getExternalData().getWorld()||worn==null||
           worn.container()!=active.armorContainer||!ChannelInteraction.sameWornItem(active.expected,worn.stack())||inputs==null||
           !ArmorCastingSystem.STORM_ROOT_ID.equals(inputs.getInteractionId(ArmorCastingSystem.STORM_INPUT))){state.active=null;return;}
        active.expected=worn.stack();active.elapsed+=dt;
        if(active.elapsed+1e-6>=DURATION){state.active=null;return;}
        if(active.waves<WAVES&&active.elapsed+1e-6>=active.nextWave)wave(owner,active,buffer);
    }
    private static void wave(Ref<EntityStore> owner,Session active,CommandBuffer<EntityStore> buffer){
        active.waves++;active.nextWave=active.elapsed+INTERVAL;
        if(active.waves==1){
            active.visualOrigin=ground(active.anchor,buffer).add(0,.06,0);
            active.visualScale=visualScale(active.visualOrigin,buffer);
            if(active.visualScale>0)
                ParticleUtil.spawnParticleEffect("ABTT_Torment_Cloud",active.visualOrigin,0,0,0,active.visualScale,(float)DURATION,buffer);
        }
        if(active.visualScale>0){
            String strike=(active.waves%2==1)?"ABTT_Torment_Strike_A":"ABTT_Torment_Strike_B";
            ParticleUtil.spawnParticleEffect(strike,active.visualOrigin,0,0,0,active.visualScale,1.6f,buffer);
        }
        ChannelInteraction.sound("SFX_ABTT_Channel",active.anchor,buffer);
        var victims=new ArrayList<Victim>();
        for(var ref:TargetUtil.getAllEntitiesInSphere(active.anchor,RADIUS+3,buffer)){
            if(ref==null||!ref.isValid()||ref.equals(owner)||!living(ref,buffer)||buffer.getComponent(ref,Player.getComponentType())!=null||
               buffer.getComponent(ref,NPCEntity.getComponentType())==null)continue;
            var transform=buffer.getComponent(ref,TransformComponent.getComponentType());var bounds=buffer.getComponent(ref,BoundingBox.getComponentType());
            if(transform==null||bounds==null)continue;
            var p=transform.getPosition();var box=bounds.getBoundingBox();
            var point=new Vector3d(Math.clamp(active.anchor.x,p.x+box.min.x,p.x+box.max.x),Math.clamp(active.anchor.y,p.y+box.min.y,p.y+box.max.y),Math.clamp(active.anchor.z,p.z+box.min.z,p.z+box.max.z));
            double distance=point.distanceSquared(active.anchor);
            if(distance<=RADIUS*RADIUS&&visible(active.anchor,point,buffer))victims.add(new Victim(ref,point,distance));
        }
        victims.sort(Comparator.comparingDouble(Victim::distance).thenComparingInt(v->v.ref().getIndex()));
        active.lastTargets=Math.min(MAX_TARGETS,victims.size());
        Set<Ref<EntityStore>> accepted=new HashSet<>();
        int hitEffects=0;
        // Rotate a bounded slice so a dense crowd does not permanently shield the same farther NPCs.
        int start=victims.isEmpty()?0:((active.waves-1)*MAX_TARGETS)%victims.size();
        for(int i=0;i<active.lastTargets;i++){
            var victim=victims.get((start+i)%victims.size());
            var hit=ChannelInteraction.applyAbilityHit(owner,victim.ref(),victim.point(),DAMAGE,ArmorCastingSystem.STORM_INPUT,ORIGIN,buffer);
            if(hit.isCancelled()||hit.getAmount()<=0||!Float.isFinite(hit.getAmount()))continue;
            active.totalHits++;accepted.add(victim.ref());
            int contact=active.contacts.merge(victim.ref(),1,Integer::sum);
            if(contact>=3)ChannelInteraction.addEffect(owner,victim.ref(),"ABTT_Conductive",false,buffer);
            if(contact>=5)ChannelInteraction.addEffect(owner,victim.ref(),"ABTT_Overload_Burn",true,buffer);
            if(hitEffects<MAX_HIT_EFFECTS){
                ParticleUtil.spawnParticleEffect("ABTT_Torment_Hit",victim.point(),buffer);
                hitEffects++;
            }
        }
        active.contacts.keySet().retainAll(accepted);
    }
    public static boolean visible(Vector3d from,Vector3d to,CommandBuffer<EntityStore> buffer){
        var ray=new Vector3d(to).sub(from);double length=ray.length();if(length<.02)return true;ray.div(length);
        var wall=TargetUtil.getTargetLocation(buffer.getExternalData().getWorld(),ChannelInteraction::blocksLightning,from.x,from.y,from.z,ray.x,ray.y,ray.z,Math.max(0,length-.01));
        return wall==null||from.distance(wall)>=length-.015;
    }
    private static float visualScale(Vector3d base,CommandBuffer<EntityStore> buffer){
        var roof=TargetUtil.getTargetLocation(buffer.getExternalData().getWorld(),ChannelInteraction::blocksLightning,
            base.x,base.y,base.z,0,1,0,STORM_CLEARANCE);
        if(roof==null)return 1;
        double height=Math.clamp(roof.y-base.y-.05,0,STORM_CLEARANCE);
        return height>.1?(float)(height/STORM_CLEARANCE):0;
    }
    private static Vector3d ground(Vector3d at,CommandBuffer<EntityStore> buffer){
        var floor=TargetUtil.getTargetLocation(buffer.getExternalData().getWorld(),ChannelInteraction::blocksLightning,at.x,at.y+.05,at.z,0,-1,0,6);
        return floor==null?new Vector3d(at):new Vector3d(floor).add(0,.02,0);
    }
    private static boolean living(Ref<EntityStore> ref,ComponentAccessor<EntityStore> accessor){
        var stats=accessor.getComponent(ref,EntityStatMap.getComponentType());var health=stats==null?null:stats.get(DefaultEntityStatTypes.getHealth());
        return health!=null&&health.get()>health.getMin()&&accessor.getComponent(ref,DeathComponent.getComponentType())==null;
    }
    private static boolean finite(Vector3d vector){return Double.isFinite(vector.x)&&Double.isFinite(vector.y)&&Double.isFinite(vector.z);}
}
