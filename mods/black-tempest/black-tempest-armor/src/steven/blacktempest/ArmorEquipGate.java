package steven.blacktempest;

import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.*;
import com.hypixel.hytale.server.core.inventory.container.filter.*;
import com.hypixel.fastutil.ints.Int2ObjectConcurrentHashMap;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Modifier;
import java.util.*;
import java.util.function.BooleanSupplier;
import java.util.function.Consumer;

/** Adds only a Mage check for exact BlackTempest IDs, preserving the live native/mod filter.
 * The pinned server exposes a filter setter without a getter. Reflection reads that one private
 * filter table; restoration changes a slot only while its current filter is still our wrapper.
 * The exact Crimson Brotherhood 0.1.1 Gate contract is read only to find an already-owned gate
 * and discard transparent inactive delegates. Only this plugin's wrapper links can change;
 * foreign wrapper links are never changed. */
// Safe-return mechanics adapted from the workspace Crimson Brotherhood runtime; no art or item assets are reused.
public final class ArmorEquipGate implements AutoCloseable {
    private static final Set<String> IDS = new HashSet<>();
    static { for (var piece : AffinityRules.GATED_PIECES) IDS.add(piece.itemId()); }
    private static final String BROTHERHOOD_GATE = "steven.brotherhood.ArmorEquipGate$Gate";
    private static final int MAX_RECOGNIZED_DEPTH = 64;
    private static final Map<Class<?>,Field[]> BROTHERHOOD_FIELDS = new java.util.concurrent.ConcurrentHashMap<>();
    private record Entry(ItemContainer container, short slot, Int2ObjectConcurrentHashMap<SlotFilter> table, Gate wrapper) {}
    private record Chain(SlotFilter root, SlotFilter normalized, Gate owned, Map<Gate,SlotFilter> compacted, int retainedDepth) {}
    private final List<Entry> entries = new ArrayList<>();
    private boolean closed;
    private static final class Gate implements SlotFilter {
        volatile SlotFilter previous; volatile BooleanSupplier primaryMage; volatile Consumer<String> rejected;
        volatile boolean active = true;
        Gate(SlotFilter previous, BooleanSupplier eligible, Consumer<String> rejected) {
            this.previous=previous; primaryMage=eligible; this.rejected=rejected;
        }
        @Override public boolean test(FilterActionType action, ItemContainer container, short slot, ItemStack stack) {
            SlotFilter delegate=previous;
            if (delegate != null && !delegate.test(action,container,slot,stack)) return false;
            if (!active || !isBlackTempest(stack)) return true;
            var armor=stack.getItem().getArmor();
            boolean nativeSlot=armor != null && armor.getArmorSlot().getValue()==slot;
            boolean allowed=stack.getQuantity()==1 && nativeSlot && primaryMage.getAsBoolean();
            if (!allowed) rejected.accept("Black Tempest armor requires a primary Mage class or its ascended path.");
            return allowed;
        }
    }
    public static boolean isBlackTempest(ItemStack stack) { return stack != null && !ItemStack.isEmpty(stack) && IDS.contains(stack.getItemId()); }
    private static Field[] brotherhoodFields(Class<?> type) {
        return BROTHERHOOD_FIELDS.computeIfAbsent(type,key->{
            try {
                Field previous=key.getDeclaredField("previous"),active=key.getDeclaredField("active");
                if(previous.getType()!=SlotFilter.class || active.getType()!=boolean.class ||
                    Modifier.isStatic(previous.getModifiers()) || Modifier.isStatic(active.getModifiers()))
                    throw new IllegalStateException("Unexpected previous/active field types");
                previous.setAccessible(true);active.setAccessible(true);
                return new Field[]{previous,active};
            } catch(ReflectiveOperationException | RuntimeException error) {
                throw new IllegalStateException("Crimson Brotherhood armor-filter contract changed; expected 0.1.1 Gate.previous/active. " +
                    "Black Tempest left the filter unchanged; update the armor compatibility adapter",error);
            }
        });
    }
    private boolean owns(ItemContainer container,short slot,Gate gate) {
        for(var row:entries)if(row.container()==container && row.slot()==slot && row.wrapper()==gate)return true;
        return false;
    }
    /** Inspect the entire recognized prefix before changing any slot. An opaque filter is a
     * boundary, not an invitation to crawl arbitrary fields. Even finding our gate cannot excuse
     * a cycle farther down: native delegation would still recurse through it on an ADD. */
    private Chain inspect(ItemContainer container,short slot,SlotFilter root,Set<Gate> deactivating) {
        var seen=Collections.newSetFromMap(new IdentityHashMap<SlotFilter,Boolean>());
        var inactive=Collections.newSetFromMap(new IdentityHashMap<SlotFilter,Boolean>());
        var links=new IdentityHashMap<SlotFilter,SlotFilter>();
        SlotFilter cursor=root,normalized=root;Gate owned=null;boolean inactiveHead=true;int depth=0;
        while(cursor!=null) {
            boolean ours=cursor instanceof Gate;
            if(!ours && !cursor.getClass().getName().equals(BROTHERHOOD_GATE))break;
            if(!seen.add(cursor) || ++depth>MAX_RECOGNIZED_DEPTH)
                throw new IllegalStateException("Malformed armor-filter chain at slot " + slot +
                    ": recognized cycle or depth over " + MAX_RECOGNIZED_DEPTH +
                    ". Black Tempest left the filter unchanged; recreate the armor container or update the conflicting armor plugin");
            SlotFilter previous;boolean active;
            if(ours) {
                var gate=(Gate)cursor;previous=gate.previous;active=gate.active && !deactivating.contains(gate);
                if(active && owned==null && owns(container,slot,gate))owned=gate;
            } else {
                var fields=brotherhoodFields(cursor.getClass());
                try { previous=(SlotFilter)fields[0].get(cursor);active=fields[1].getBoolean(cursor); }
                catch(IllegalAccessException error) { throw new IllegalStateException("Cannot read pinned Crimson Brotherhood armor-filter contract; filter unchanged",error); }
            }
            // Both verified Gate.test implementations do only previous delegation when inactive.
            // Peeling at the HEAD needs no foreign link mutation.
            links.put(cursor,previous);if(!active)inactive.add(cursor);
            if(inactiveHead && !active)normalized=previous;
            else inactiveHead=false;
            cursor=previous;
        }
        var compacted=new IdentityHashMap<Gate,SlotFilter>();
        for(var link:links.entrySet())if(link.getKey() instanceof Gate gate) {
            SlotFilter previous=link.getValue();
            while(inactive.contains(previous))previous=links.get(previous);
            if(previous!=link.getValue())compacted.put(gate,previous);
        }
        int retainedDepth=0;
        for(cursor=normalized;cursor!=null && links.containsKey(cursor);) {
            retainedDepth++;
            cursor=cursor instanceof Gate gate && compacted.containsKey(gate)?compacted.get(gate):links.get(cursor);
        }
        return new Chain(root,normalized,owned,compacted,retainedDepth);
    }
    @SuppressWarnings("unchecked")
    private static Int2ObjectConcurrentHashMap<SlotFilter> table(ItemContainer container) {
        Class<?> type = container instanceof SimpleItemContainer ? SimpleItemContainer.class :
            container instanceof DelegateItemContainer<?> ? DelegateItemContainer.class : null;
        if (type == null) throw new IllegalStateException("Unsupported armor container for safe BlackTempest class gate: " + container.getClass().getName());
        try {
            Field field=type.getDeclaredField("slotFilters");field.setAccessible(true);
            var all=(Map<FilterActionType,Int2ObjectConcurrentHashMap<SlotFilter>>)field.get(container);
            var current=all.get(FilterActionType.ADD);
            if(current==null) {
                // Force native creation of the ADD map without accepting or removing any items.
                container.setSlotFilter(FilterActionType.ADD,(short)0,SlotFilter.ALLOW);
                current=all.get(FilterActionType.ADD);
                current.remove(0);
            }
            return current;
        } catch (ReflectiveOperationException error) { throw new IllegalStateException("Pinned Hytale armor-filter API changed; BlackTempest equipment gate cannot initialize",error); }
    }
    public synchronized void bind(ItemContainer container, BooleanSupplier eligible, Consumer<String> rejected) {
        if (closed) throw new IllegalStateException("Armor class gate closed");
        if (container==null) return;
        var filters=table(container);
        var plans=new LinkedHashMap<Short,Chain>();
        for(var piece:AffinityRules.GATED_PIECES) {
            short slot=(short)com.hypixel.hytale.protocol.ItemArmorSlot.valueOf(piece.slot().name()).getValue();
            if(slot>=container.getCapacity())continue;
            var chain=inspect(container,slot,filters.get((int)slot),Set.of());
            if(chain.owned()==null && chain.retainedDepth()>=MAX_RECOGNIZED_DEPTH)
                throw new IllegalStateException("Cannot add Black Tempest armor gate at slot " + slot +
                    ": recognized depth would exceed " + MAX_RECOGNIZED_DEPTH +
                    ". Filter unchanged; recreate the armor container or update the conflicting armor plugin");
            plans.put(slot,chain);
        }
        // Inactive wrappers may be buried by a new active Brotherhood wrapper before our bind.
        // Compact only our class's links after ALL slots validate. This also covers an inactive
        // Black Tempest wrapper from a previous instance, without ever rewriting Brotherhood.
        for(var chain:plans.values())for(var link:chain.compacted().entrySet())link.getKey().previous=link.getValue();
        for(var plan:plans.entrySet()) {
            short slot=plan.getKey();var chain=plan.getValue();
            if(chain.owned()!=null) {
                chain.owned().primaryMage=eligible;chain.owned().rejected=rejected;
                if(chain.normalized()!=chain.root())container.setSlotFilter(FilterActionType.ADD,slot,chain.normalized());
                continue;
            }
            var gate=new Gate(chain.normalized(),eligible,rejected);
            container.setSlotFilter(FilterActionType.ADD,slot,gate);
            entries.add(new Entry(container,slot,filters,gate));
        }
    }
    /** Native atomic moves preserve exact metadata and remove the source only after destination accepts it. */
    public static int evacuate(ItemContainer armor, ArmorReturnState pending) {
        if(armor==null)return 0;
        int moved=0;
        for(short slot=0;slot<armor.getCapacity();slot++) {
            var stack=armor.getItemStack(slot);
            if(!isBlackTempest(stack))continue;
            pending.ensureRoom(stack);
            // Only owned class-invalid gear moves to private escrow. Ignore a foreign REMOVE
            // prohibition for this mandatory safe return; leave that filter installed for ordinary UI use.
            var transaction=armor.moveItemStackFromSlot(slot,pending.inventory(),true,false);
            if(transaction.succeeded()) { moved++;pending.changed(); }
            else throw new IllegalStateException("Could not safely return invalid-class BlackTempest armor; original item preserved");
        }
        return moved;
    }
    private static void nativeLock(ItemContainer container,String method) {
        try {
            Method action=ItemContainer.class.getDeclaredMethod(method);action.setAccessible(true);action.invoke(container);
        } catch(ReflectiveOperationException error) {
            Throwable cause=error instanceof InvocationTargetException && error.getCause()!=null?error.getCause():error;
            throw new IllegalStateException("Pinned Hytale container locking API changed",cause);
        }
    }
    /** Insert into one empty destination slot before removing our private source. The native
     * whole-stack move removes its source before a foreign ADD filter can throw, so it is not
     * used here. Both containers remain write-locked; native calls are reentrant on these locks.
     * A foreign post-insert event exception is reconciled from the exact inserted item once. */
    public static int returnPending(ArmorReturnState pending,ItemContainer... destinations) {
        if(pending==null)return 0;
        int returned=0;RuntimeException failure=null;
        var source=pending.inventory();
        nativeLock(source,"lockForWrite");
        try {
            for(short slot=0;slot<source.getCapacity();slot++) {
                var held=source.getItemStack(slot);
                if(ItemStack.isEmpty(held))continue;
                for(var destination:destinations) {
                    if(destination==null || destination==source)continue;
                    boolean locked=false;
                    try {
                        nativeLock(destination,"lockForWrite");locked=true;
                        for(short target=0;target<destination.getCapacity() && !ItemStack.isEmpty(source.getItemStack(slot));target++) {
                            if(!ItemStack.isEmpty(destination.getItemStack(target)))continue;
                            var original=source.getItemStack(slot);var one=original.withQuantity(1);
                            RuntimeException insertionError=null;
                            try { destination.setItemStackForSlot(target,one); }
                            catch(RuntimeException error) { insertionError=error; }
                            var after=destination.getItemStack(target);
                            if(one.equals(after)) {
                                // Private unfiltered storage cannot invoke a foreign filter or listener.
                                var removed=source.removeItemStackFromSlot(slot,1,false,false);
                                if(!removed.succeeded())throw new IllegalStateException("Private BlackTempest source changed during locked return");
                                pending.changed();returned++;
                            }
                            if(insertionError!=null)throw insertionError;
                        }
                    } catch(RuntimeException error) { if(failure==null)failure=error; }
                    finally { if(locked)nativeLock(destination,"unlockForWrite"); }
                    if(ItemStack.isEmpty(source.getItemStack(slot)))break;
                }
            }
        } finally { nativeLock(source,"unlockForWrite"); }
        if(failure!=null)throw new IllegalStateException("A destination rejected safe BlackTempest return; untransferred pieces remain in persisted storage",failure);
        return returned;
    }
    @Override public synchronized void close() {
        if(closed)return;
        var deactivating=Collections.newSetFromMap(new IdentityHashMap<Gate,Boolean>());
        for(var row:entries)deactivating.add(row.wrapper());
        var plans=new IdentityHashMap<ItemContainer,Map<Short,Chain>>();
        for(var row:entries) {
            var slots=plans.computeIfAbsent(row.container(),key->new LinkedHashMap<>());
            if(!slots.containsKey(row.slot()))slots.put(row.slot(),inspect(row.container(),row.slot(),row.table().get((int)row.slot()),deactivating));
        }
        closed=true;
        for(var row:entries)row.wrapper().active=false;
        // Brotherhood may have closed since our last bind. Plan against our pending inactive
        // state before any mutation, then trim newly transparent tails before restoring them.
        for(var slots:plans.values())for(var chain:slots.values())
            for(var link:chain.compacted().entrySet())link.getKey().previous=link.getValue();
        for(var row:entries) {
            if(row.table().get((int)row.slot())!=row.wrapper())continue;
            SlotFilter previous=row.wrapper().previous;
            if(previous==null)row.table().remove((int)row.slot());
            else row.container().setSlotFilter(FilterActionType.ADD,row.slot(),previous);
        }
        entries.clear();
    }
}
