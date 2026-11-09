package steven.rangersnipers;

import com.hypixel.hytale.protocol.Position;
import com.hypixel.hytale.protocol.SoundCategory;
import com.hypixel.hytale.protocol.packets.world.PlaySoundEvent3D;
import org.joml.Vector3dc;
import java.util.*;
import java.util.function.*;

/** Optional audio-only once gate. Tokens identify a shell, never an ammo unit. */
public final class OwnerTailGate {
    private final Map<Object,Long> seen=new LinkedHashMap<>();
    private final Consumer<Throwable> diagnostic;
    private final LongSupplier clock;
    private long nextDiagnostic;
    public OwnerTailGate(Consumer<Throwable> diagnostic){this(diagnostic,System::nanoTime);}
    public OwnerTailGate(Consumer<Throwable> diagnostic,LongSupplier clock){this.diagnostic=diagnostic;this.clock=clock;}
    public synchronized boolean emit(Object shot,Object owner,int pelletIndex,boolean committedWeapon,int eventIndex,
                                      Vector3dc origin,BiConsumer<Object,PlaySoundEvent3D> send){
        try{
            if(shot==null||owner==null||pelletIndex>0||!committedWeapon||eventIndex<=0||origin==null||
               !Double.isFinite(origin.x())||!Double.isFinite(origin.y())||!Double.isFinite(origin.z()))return false;
            long now=clock.getAsLong();
            seen.entrySet().removeIf(e->now-e.getValue()>10_000_000_000L);
            if(seen.containsKey(shot))return false;
            if(seen.size()>=2048)seen.remove(seen.keySet().iterator().next());
            // Claim before transport: a failed optional effect is never retried as
            // duplicate audio. Immutable primitive coordinates leave entity motion behind.
            seen.put(shot,now);
            var packet=new PlaySoundEvent3D(eventIndex,SoundCategory.SFX,new Position(origin.x(),origin.y(),origin.z()),1,1);
            send.accept(owner,packet);return true;
        }catch(Throwable error){warn(error);return false;}
    }
    public synchronized void warn(Throwable error){
        try{long now=clock.getAsLong();if(now>=nextDiagnostic){nextDiagnostic=now+30_000_000_000L;diagnostic.accept(error);}}catch(Throwable ignored){}
    }
}
