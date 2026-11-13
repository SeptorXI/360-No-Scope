package steven.abtt;

import com.hypixel.hytale.builtin.beam.AttachedBeam;
import com.hypixel.hytale.builtin.beam.BeamComponent;
import com.hypixel.hytale.builtin.beam.asset.Beam;
import com.hypixel.hytale.component.*;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import org.joml.Vector3d;
import org.joml.Vector3f;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/** Native endpoint beams: source follows the rendered hand bone in FPS/TPS, width never scales with range. */
public final class FingertipBeams {
    public static final String BEAM_ID="ABTT_Lightning";
    public static final float WIDTH=.035f;
    /** Hide the long effect when the camera target lies inside the raised-fingertip envelope. */
    public static final double MIN_FORWARD=1.4;
    public static final double END_MARGIN=.04;
    private FingertipBeams(){}
    private static final Map<Ref<EntityStore>,BeamComponent> PENDING=new ConcurrentHashMap<>();
    public record Anchor(String node,float x,float y,float z){public Vector3f offset(){return new Vector3f(x,y,z);}}
    // Exact authored hand-space contact points, in blocks (the armor model uses 64 units per block).
    private static final List<Anchor> ANCHORS=List.of(
        new Anchor("R-Hand",(float)(6.536422561946562/64),(float)(-20.46334058060603/64),(float)(.2/64)),
        new Anchor("R-Hand",(float)(2.2856010267825644/64),(float)(-22.58204690528492/64),(float)(.2/64)),
        new Anchor("R-Hand",(float)(-2.2332650705396206/64),(float)(-21.58341737053034/64),(float)(.2/64)),
        new Anchor("R-Hand",(float)(-6.5538465944359965/64),(float)(-19.446558305423302/64),(float)(.2/64)),
        new Anchor("R-Hand",(float)(14.090169943749473/64),(float)(-8.577852522924733/64),0),
        new Anchor("L-Hand",(float)(-6.536422561946562/64),(float)(-20.46334058060603/64),(float)(.2/64)),
        new Anchor("L-Hand",(float)(-2.2856010267825644/64),(float)(-22.58204690528492/64),(float)(.2/64)),
        new Anchor("L-Hand",(float)(2.2332650705396206/64),(float)(-21.58341737053034/64),(float)(.2/64)),
        new Anchor("L-Hand",(float)(6.5538465944359965/64),(float)(-19.446558305423302/64),(float)(.2/64)),
        new Anchor("L-Hand",(float)(-14.090169943749473/64),(float)(-8.577852522924733/64),0));
    public static List<Anchor> anchors(){return ANCHORS;}
    public static final class State {
        private Ref<EntityStore> owner;
        private BeamComponent component;
        private final Set<AttachedBeam> owned=Collections.newSetFromMap(new IdentityHashMap<>());
    }
    public static int ownedCount(State state){return state.owned.size();}
    /** A finite forward endpoint, just before the native hit surface; null suppresses point-blank/backward rays. */
    public static Vector3d endpoint(Vector3d origin,Vector3d forward,Vector3d hit){
        if(origin==null||forward==null||hit==null||!origin.isFinite()||!forward.isFinite()||!hit.isFinite()||forward.lengthSquared()<.99)return null;
        var direction=new Vector3d(forward).normalize();
        var delta=new Vector3d(hit).sub(origin);
        double length=delta.length(),projection=delta.dot(direction);
        if(!Double.isFinite(length)||projection<MIN_FORWARD+END_MARGIN||length<MIN_FORWARD+END_MARGIN)return null;
        // Production hit points lie on the camera ray. Reject off-axis supplied endpoints instead of drawing rearward branches.
        if(projection/length<.999)return null;
        double distance=Math.min(ChannelRules.RANGE,length)-END_MARGIN;
        if(distance<MIN_FORWARD)return null;
        return new Vector3d(direction).mul(distance).add(origin);
    }
    /** Updates ten records on the existing actor; other addons' beams are retained even when equal by value. */
    public static void update(Ref<EntityStore> owner,State state,Vector3d origin,Vector3d forward,Vector3d hit,ComponentAccessor<EntityStore> accessor){
        if(owner==null||!owner.isValid()||accessor==null||state==null)return;
        if(state.owner!=null&&!state.owner.equals(owner))return;
        state.owner=owner;
        var target=endpoint(origin,forward,hit);
        var current=accessor.getComponent(owner,BeamComponent.getComponentType());
        if(current==null)current=PENDING.get(owner);
        if(state.component!=null&&state.component!=current)removeOwned(state.component,state.owned);
        if(current!=null)removeOwned(current,state.owned);
        state.owned.clear();
        if(target==null){state.component=current;return;}
        int index=Beam.getAssetMap().getIndex(BEAM_ID);
        if(index<0)return; // Cosmetic asset failure must never charge extra, stop combat or replace foreign visuals.
        if(current==null){
            if(accessor instanceof CommandBuffer<EntityStore> buffer){
                current=new BeamComponent();
                var pending=current;PENDING.put(owner,pending);
                buffer.run(store->{try{
                    if(!owner.isValid())return;
                    var installed=store.getComponent(owner,BeamComponent.getComponentType());
                    if(installed==null)store.addComponent(owner,BeamComponent.getComponentType(),pending);
                    else if(installed!=pending&&BeamComponent.MAX_BEAMS-installed.getBeams().size()>=pending.getBeams().size())
                        for(var beam:pending.getBeams())installed.add(beam);
                }finally{PENDING.remove(owner,pending);}});
            }else current=accessor.ensureAndGetComponent(owner,BeamComponent.getComponentType());
        }
        state.component=current;
        if(current==null||BeamComponent.MAX_BEAMS-current.getBeams().size()<ANCHORS.size())return;
        for(var anchor:ANCHORS){
            var beam=AttachedBeam.toPosition(index,WIDTH,WIDTH,anchor.node(),anchor.offset(),new Vector3d(target));
            current.add(beam);state.owned.add(beam);
        }
    }
    /** Removes this session's identities only; a delayed old-session cleanup cannot erase a new cast. */
    public static void clear(Ref<EntityStore> owner,State state,ComponentAccessor<EntityStore> accessor){
        if(state==null||state.owner==null||!state.owner.equals(owner))return;
        if(state.component!=null)removeOwned(state.component,state.owned);
        if(owner!=null&&owner.isValid()&&accessor!=null){
            var current=accessor.getComponent(owner,BeamComponent.getComponentType());
            if(current!=null&&current!=state.component)removeOwned(current,state.owned);
        }
        state.owned.clear();state.component=null;
    }
    private static void removeOwned(BeamComponent component,Set<AttachedBeam> owned){
        if(owned.isEmpty())return;
        var retained=new ArrayList<AttachedBeam>(component.getBeams().size());
        for(var beam:component.getBeams())if(!owned.contains(beam))retained.add(beam);
        // Native remove uses value equality. Identity filtering preserves even an equal foreign record.
        if(retained.size()!=component.getBeams().size())component.set(retained);
    }
}
