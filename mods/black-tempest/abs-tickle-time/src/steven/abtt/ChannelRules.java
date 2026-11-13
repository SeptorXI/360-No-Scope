package steven.abtt;

/** Authored base values; native race/class/skill/food/enchantment damage hooks run afterwards. */
public final class ChannelRules {
    public static final String ITEM_ID = "Weapon_Gauntlets_AB_Tickle_Time";
    public static final String CAUSE_ID = "Lightning";
    public static final float INTERVAL = 0.2f;
    public static final double RANGE = 10.0;
    public static final double RAY_EPSILON = 1e-7;
    public static final float DAMAGE = 10f;
    public static final float MANA = 2.4f;
    public static final float STAMINA = 0.3f;
    public static final double DURABILITY = 0.1;
    public static final int SLOW_PULSES = 6;
    public static final int SCORCH_PULSES = 11;
    private ChannelRules() {}
    public static boolean canPay(float mana, float minMana, float stamina, float minStamina) {
        return Float.isFinite(mana) && Float.isFinite(minMana) && Float.isFinite(stamina) && Float.isFinite(minStamina)
            && mana - Math.max(0,minMana) + 1e-6f >= MANA && stamina - Math.max(0,minStamina) + 1e-6f >= STAMINA;
    }
    /** Slab intersection returns first contact along a normalized ray, never center-distance targeting. */
    public static double rayBox(double ox,double oy,double oz,double dx,double dy,double dz,
                                double minX,double minY,double minZ,double maxX,double maxY,double maxZ,double limit) {
        double[] o={ox,oy,oz},d={dx,dy,dz},lo={minX,minY,minZ},hi={maxX,maxY,maxZ};
        double near=0,far=limit;
        for(int i=0;i<3;i++) {
            if(!Double.isFinite(o[i])||!Double.isFinite(d[i])||!Double.isFinite(lo[i])||!Double.isFinite(hi[i]))return Double.POSITIVE_INFINITY;
            if(Math.abs(d[i])<1e-10) {if(o[i]<lo[i]||o[i]>hi[i])return Double.POSITIVE_INFINITY;}
            else {double a=(lo[i]-o[i])/d[i],b=(hi[i]-o[i])/d[i];
                near=Math.max(near,Math.min(a,b));far=Math.min(far,Math.max(a,b));
                if(near>far+RAY_EPSILON)return Double.POSITIVE_INFINITY;}
        }
        return near<=limit+RAY_EPSILON?Math.min(near,limit):Double.POSITIVE_INFINITY;
    }
}
