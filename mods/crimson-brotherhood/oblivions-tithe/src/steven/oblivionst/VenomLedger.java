package steven.oblivionst;

import java.util.*;
import java.util.function.Predicate;

/** World-thread-owned, bounded poison timing and per-stack attribution. */
public final class VenomLedger<T> {
    public static final int MAX_STACKS=10;
    public static final double DAMAGE_PER_STACK=2, INTERVAL=1, DURATION=6;
    private static final double EPS=1e-6;
    private final ArrayDeque<T> owners=new ArrayDeque<>();
    private double time,expiry,nextTick;
    public VenomLedger(){}
    private VenomLedger(VenomLedger<T> other){owners.addAll(other.owners);time=other.time;expiry=other.expiry;nextTick=other.nextTick;}
    public VenomLedger<T> copy(){return new VenomLedger<>(this);}
    public int stacks(){return owners.size();}
    public double time(){return time;}
    public double expiresAt(){return expiry;}
    public double nextTickAt(){return nextTick;}
    public boolean active(){return !owners.isEmpty();}
    public void clear(){owners.clear();expiry=nextTick=0;}
    public void removeOwners(Predicate<T> invalid){owners.removeIf(invalid);if(owners.isEmpty())clear();}
    public Map<T,Integer> portions(){
        Map<T,Integer> result=new LinkedHashMap<>();
        for(T owner:owners)result.merge(owner,1,Integer::sum);
        return Collections.unmodifiableMap(result);
    }
    /** At cap only the oldest contribution changes hands, never the whole pool. */
    public void hit(T owner){
        Objects.requireNonNull(owner,"owner");
        if(time>expiry+EPS)clear();
        if(owners.isEmpty())nextTick=time+INTERVAL;
        if(owners.size()==MAX_STACKS)owners.removeFirst();
        owners.addLast(owner);expiry=time+DURATION;
    }
    /** At most one pulse per server tick; lag never bursts six poison hits at once. */
    public Map<T,Integer> advance(double dt){
        if(!Double.isFinite(dt)||dt<0)throw new IllegalArgumentException("Invalid poison dt");
        time+=dt;
        if(!active())return Map.of();
        if(time>expiry+EPS){clear();return Map.of();}
        Map<T,Integer> pulse=Map.of();
        if(time+EPS>=nextTick){
            pulse=portions();
            double skipped=Math.max(1,Math.floor((time-nextTick+EPS)/INTERVAL)+1);
            nextTick+=skipped*INTERVAL;
        }
        if(time+EPS>=expiry)clear();
        return pulse;
    }
}
