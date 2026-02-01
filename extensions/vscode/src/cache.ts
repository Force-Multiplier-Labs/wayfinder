/**
 * Cache entry containing value and expiration time
 */
export interface CacheEntry<T> {
  /** Cached value */
  value: T;
  /** Expiration timestamp (milliseconds since epoch) */
  expiresAt: number;
}

/**
 * Generic cache implementation with TTL support and automatic cleanup
 */
export class Cache<T> {
  private readonly store = new Map<string, CacheEntry<T>>();
  private readonly defaultTtlMs: number;
  private cleanupTimer?: ReturnType<typeof setInterval>;

  /**
   * Creates a new cache instance
   * @param defaultTtlMs Default time-to-live in milliseconds
   */
  constructor(defaultTtlMs: number = 300000) { // Default 5 minutes
    this.defaultTtlMs = defaultTtlMs;

    // Schedule periodic cleanup every minute
    this.cleanupTimer = setInterval(() => {
      this.cleanup();
    }, 60000);
  }

  /**
   * Retrieves a value from the cache if it exists and hasn't expired
   * @param key Cache key
   * @returns Cached value or undefined if not found/expired
   */
  get(key: string): T | undefined {
    const entry = this.store.get(key);

    if (!entry) {
      return undefined;
    }

    const now = Date.now();
    if (entry.expiresAt <= now) {
      // Entry expired, remove it
      this.store.delete(key);
      return undefined;
    }

    return entry.value;
  }

  /**
   * Stores a value in the cache with optional TTL override
   * @param key Cache key
   * @param value Value to cache
   * @param ttlMs Time-to-live in milliseconds (optional, uses default if not provided)
   */
  set(key: string, value: T, ttlMs?: number): void {
    const ttl = ttlMs ?? this.defaultTtlMs;
    const expiresAt = Date.now() + ttl;

    this.store.set(key, { value, expiresAt });
  }

  /**
   * Removes a specific entry from the cache
   * @param key Cache key to invalidate
   */
  invalidate(key: string): void {
    this.store.delete(key);
  }

  /**
   * Clears all entries from the cache
   */
  clear(): void {
    this.store.clear();
  }

  /**
   * Returns the current number of entries in the cache
   * @returns Cache size
   */
  size(): number {
    return this.store.size;
  }

  /**
   * Disposes the cache and clears the cleanup timer
   */
  dispose(): void {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
      this.cleanupTimer = undefined;
    }
    this.clear();
  }

  /**
   * Removes expired entries from the cache (private cleanup method)
   */
  private cleanup(): void {
    const now = Date.now();
    const keysToDelete: string[] = [];

    // Collect expired keys
    for (const [key, entry] of this.store.entries()) {
      if (entry.expiresAt <= now) {
        keysToDelete.push(key);
      }
    }

    // Remove expired entries
    keysToDelete.forEach(key => this.store.delete(key));

    // Log cleanup activity if significant
    if (keysToDelete.length > 0) {
      console.log(`ContextCore Cache: Cleaned up ${keysToDelete.length} expired entries`);
    }
  }
}
