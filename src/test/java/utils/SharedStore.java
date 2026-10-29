package utils;

import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Almacen global en memoria para compartir datos entre escenarios y features.
 * Los valores se guardan como JSON (String) desde karate-config.js.
 */
public final class SharedStore {

    private static final Map<String, String> DATA = new ConcurrentHashMap<>();
    private static final Set<String> PHONES = ConcurrentHashMap.newKeySet();

    private SharedStore() {
    }

    public static void put(String key, String json) {
        DATA.put(key, json);
    }

    public static String get(String key) {
        return DATA.get(key);
    }

    public static boolean contains(String key) {
        return DATA.containsKey(key);
    }

    /** Devuelve true si el numero no se habia emitido antes en esta ejecucion. */
    public static boolean reservePhone(String phone) {
        return PHONES.add(phone);
    }

    public static void clear() {
        DATA.clear();
        PHONES.clear();
    }
}
