package steven.rangersnipers;

import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.modules.interaction.Interactions;
import com.hypixel.hytale.server.core.modules.projectile.component.ProjectileLaunchContext;
import com.hypixel.hytale.server.core.modules.projectile.event.ProjectileLaunchEvent;
import com.hypixel.hytale.server.core.asset.type.soundevent.config.SoundEvent;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.SoundUtil;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import org.joml.Vector3d;
import org.bson.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** One optional owner-only fixed-origin 3D tail after a paid weapon launch.
 * No entity-add assumptions, physics consumers, ammo writes or gameplay waits.
 */
public final class OwnerTailAudioSystem extends EntityEventSystem<EntityStore,ProjectileLaunchEvent> {
    public record Profile(String primaryEventId,String abilityEventId){}
    private final Map<String,Profile> profiles;
    private final OwnerTailGate gate=new OwnerTailGate(error->{try{System.err.println("[360 No Scope] Optional owner tail skipped: "+error);}catch(Throwable ignored){}});
    public OwnerTailAudioSystem(Map<String,Profile> profiles){super(ProjectileLaunchEvent.class);this.profiles=Map.copyOf(profiles);}
    public Map<String,Profile> profiles(){return profiles;}
    public static OwnerTailAudioSystem fromResource(ClassLoader loader){
        Map<String,Profile> profiles=new HashMap<>();
        try(var input=loader.getResourceAsStream("ranger-snipers-owner-tail-profiles.json")){
            if(input==null)throw new IllegalStateException("Missing ranger-snipers-owner-tail-profiles.json");
            {var doc=BsonDocument.parse(new String(input.readAllBytes(),StandardCharsets.UTF_8));
                for(var value:doc.getArray("Profiles")){var p=value.asDocument();
                    String marker=p.getString("FlightMarker").getValue(),primary=p.getString("PrimaryEventId").getValue();
                    String ability=p.containsKey("AbilityEventId")?p.getString("AbilityEventId").getValue():null;
                    if(!marker.matches("[A-Za-z0-9_]+")||!primary.matches("[A-Za-z0-9_]+")||
                       (ability!=null&&!ability.matches("[A-Za-z0-9_]+")))throw new IllegalArgumentException("Invalid audio binding ID");
                    if(profiles.put(marker,new Profile(primary,ability))!=null)throw new IllegalArgumentException("Duplicate audio flight marker");
                }
            }
            if(profiles.size()!=54)throw new IllegalStateException("Expected 54 owner-tail profiles");
        }catch(Throwable error){profiles.clear();try{System.err.println("[360 No Scope] Optional owner-tail profiles unavailable: "+error);}catch(Throwable ignored){}}
        return new OwnerTailAudioSystem(profiles);
    }
    @Override public Query<EntityStore> getQuery(){return PlayerRef.getComponentType();}
    @Override public void handle(int index,ArchetypeChunk<EntityStore> chunk,Store<EntityStore> store,
                                 CommandBuffer<EntityStore> commands,ProjectileLaunchEvent event){
        try{
            var type=event.getInteractionType();
            if(profiles.isEmpty()||!event.isLaunchedByWeapon()||(type!=InteractionType.Primary&&type!=InteractionType.Ability1))return;
            var owner=chunk.getReferenceTo(index);var projectile=event.getProjectileRef();
            // Native ProjectileInteraction and ASScatter queue their launch context
            // and pellet metadata before dispatching this event. Inspect only after
            // those commands and entity creation have executed, before physics ticks.
            commands.run(actual->dispatch(owner,projectile,type,actual));
        }catch(Throwable error){gate.warn(error);}
    }
    private void dispatch(Ref<EntityStore> owner,Ref<EntityStore> projectile,InteractionType type,Store<EntityStore> store){
        try{
            if(owner==null||!owner.isValid()||projectile==null||!projectile.isValid()||store.getComponent(owner,PlayerRef.getComponentType())==null)return;
            var context=store.getComponent(projectile,ProjectileLaunchContext.getComponentType());
            if(context==null||!context.isLaunchedByWeapon()||context.getInteractionType()!=type)return;
            var interactions=store.getComponent(projectile,Interactions.getComponentType());
            if(interactions==null)return;
            var profile=profiles.get(interactions.getInteractionId(InteractionType.ProjectileSpawn));
            if(profile==null)return;
            String eventId=type==InteractionType.Ability1?profile.abilityEventId():profile.primaryEventId();
            if(eventId==null||eventId.isBlank())return;
            int eventIndex=SoundEvent.getAssetMap().getIndex(eventId);
            if(eventIndex<=0||SoundEvent.getAssetMap().getAsset(eventIndex)==null)return;
            var flightType=RangerSnipersPlugin.flightComponentType();
            var flight=flightType==null?null:store.getComponent(projectile,flightType);
            if(flight==null)return;
            var pelletType=RangerSnipersPlugin.scatterComponentType();
            var pellet=pelletType==null?null:store.getComponent(projectile,pelletType);
            Object token=pellet==null?projectile:pellet.ledger();
            int pelletIndex=pellet==null?0:pellet.index();
            var origin=flight.originCopy();
            gate.emit(token,owner,pelletIndex,true,eventIndex,origin,(selectedOwner,packet)->
                SoundUtil.playSoundEvent3dToPlayer(owner,packet.soundEventIndex,packet.category,
                    packet.position.x,packet.position.y,packet.position.z,packet.volumeModifier,packet.pitchModifier,store));
        }catch(Throwable error){gate.warn(error);}
    }
}
