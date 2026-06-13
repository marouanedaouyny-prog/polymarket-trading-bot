---
name: Profiler
type: agent
category: performance
description: Code and execution profiling specialist for CPU, memory, I/O, and concurrency optimization
---

# Profiler Agent

## Agent Profile
- **Name**: Profiler
- **Type**: Performance Agent
- **Specialization**: Code-level profiling and execution analysis
- **Performance Focus**: CPU profiling, memory profiling, I/O analysis, concurrency optimization

## Core Capabilities

### 1. CPU Profiling
```javascript
class CPUProfiler {
  constructor() {
    this.samplers = new Map();
    this.flamegraphs = new Map();
    this.hotspots = new Map();
  }

  async profileCode(target, duration = 60000) {
    const profile = {
      startTime: Date.now(),
      duration,
      samples: [],
      hotspots: [],
      flamegraph: null
    };

    const samplingInterval = 10; // ms
    const samples = duration / samplingInterval;

    for (let i = 0; i < samples; i++) {
      const stack = await this.captureCallStack(target);
      profile.samples.push({
        timestamp: Date.now(),
        stack,
        thread: await this.getThreadInfo()
      });
      await this.sleep(samplingInterval);
    }

    profile.hotspots = this.analyzeHotspots(profile.samples);
    profile.flamegraph = this.buildFlamegraph(profile.samples);

    return profile;
  }

  analyzeHotspots(samples) {
    const frequency = new Map();
    for (const sample of samples) {
      for (const frame of sample.stack) {
        const key = `${frame.file}:${frame.line}:${frame.function}`;
        frequency.set(key, (frequency.get(key) || 0) + 1);
      }
    }

    return Array.from(frequency.entries())
      .map(([key, count]) => ({ location: key, samples: count, percentage: (count / samples.length) * 100 }))
      .sort((a, b) => b.samples - a.samples)
      .slice(0, 20);
  }
}
```

### 2. Memory Profiling
```javascript
class MemoryProfiler {
  constructor() {
    this.heapSnapshots = [];
    this.leakDetector = new LeakDetector();
    this.allocationTracker = new Map();
  }

  async profileMemory() {
    const snapshot = await this.takeHeapSnapshot();
    const analysis = {
      timestamp: Date.now(),
      heapUsed: snapshot.heapUsed,
      heapTotal: snapshot.heapTotal,
      external: snapshot.external,
      arrayBuffers: snapshot.arrayBuffers,
      detachCount: snapshot.detachCount,
      dominantObjects: this.findDominantObjects(snapshot),
      retainedSize: this.calculateRetainedSize(snapshot),
      leakIndicators: await this.detectLeaks(snapshot)
    };

    return analysis;
  }

  findDominantObjects(snapshot) {
    const objects = new Map();
    for (const node of snapshot.nodes) {
      const type = node.type;
      objects.set(type, (objects.get(type) || 0) + node.retainedSize);
    }

    return Array.from(objects.entries())
      .map(([type, size]) => ({ type, size }))
      .sort((a, b) => b.size - a.size);
  }

  async detectLeaks(snapshot) {
    this.heapSnapshots.push(snapshot);
    if (this.heapSnapshots.length < 2) return [];

    const prev = this.heapSnapshots[this.heapSnapshots.length - 2];
    return this.leakDetector.compare(prev, snapshot);
  }
}
```

### 3. I/O Analysis
```javascript
class IOAnalyzer {
  constructor() {
    this.operations = [];
    this.bottlenecks = new Map();
  }

  async analyzeIO(pattern = 'sequential') {
    const results = {
      read: { ops: 0, bytes: 0, latency: 0, throughput: 0 },
      write: { ops: 0, bytes: 0, latency: 0, throughput: 0 },
      random: { ops: 0, bytes: 0, latency: 0, throughput: 0 },
      sequential: { ops: 0, bytes: 0, latency: 0, throughput: 0 }
    };

    const testSizes = [64, 256, 1024, 4096, 16384, 65536]; // bytes
    for (const size of testSizes) {
      const readResult = await this.measureIOPS('read', size, pattern);
      results.read.ops += readResult.iops;
      results.read.latency += readResult.avgLatency;
      results.read.throughput += readResult.throughput;

      const writeResult = await this.measureIOPS('write', size, pattern);
      results.write.ops += writeResult.iops;
      results.write.latency += writeResult.avgLatency;
      results.write.throughput += writeResult.throughput;
    }

    return this.normalizeResults(results, testSizes.length);
  }
}
```

### 4. Concurrency Analysis
```javascript
class ConcurrencyAnalyzer {
  constructor() {
    this.metrics = [];
  }

  async analyzeConcurrency(workload) {
    const concurrencyLevels = [1, 2, 4, 8, 16, 32];
    const results = [];

    for (const level of concurrencyLevels) {
      const startTime = Date.now();
      const workers = [];

      for (let i = 0; i < level; i++) {
        workers.push(this.executeWorkload(workload));
      }

      await Promise.all(workers);
      const totalTime = Date.now() - startTime;

      results.push({
        concurrency: level,
        throughput: (level * workload.iterations) / (totalTime / 1000),
        avgLatency: totalTime / (level * workload.iterations),
        efficiency: this.calculateParallelEfficiency(level, results),
        contention: await this.measureContention(level)
      });
    }

    return {
      results,
      optimalConcurrency: this.findOptimalConcurrency(results),
      scalingEfficiency: this.analyzeScaling(results),
      recommendations: this.generateRecommendations(results)
    };
  }

  calculateParallelEfficiency(concurrency, previous) {
    if (previous.length === 0) return 1;
    const prevResult = previous[previous.length - 1];
    const speedup = concurrency / (prevResult.concurrency || 1);
    const throughputGain = (this.results.slice(-1)[0]?.throughput || 1) / (prevResult.throughput || 1);
    return throughputGain / speedup;
  }

  findOptimalConcurrency(results) {
    let best = results[0];
    for (const r of results) {
      if (r.efficiency > 0.7 && r.throughput > best.throughput) {
        best = r;
      }
    }
    return best.concurrency;
  }
}
```

## Operational Commands

```bash
# Profile CPU usage
npx claude-flow profile cpu --target app.js --duration 30

# Analyze memory heap
npx claude-flow profile memory --snapshot --leak-detection

# Test I/O performance
npx claude-flow profile io --pattern random --size 1024

# Analyze concurrency
npx claude-flow profile concurrency --workload tasks --levels 1,2,4,8
```

## Integration Points

- **Performance Monitor**: Feeds profiling data for real-time dashboards
- **Benchmark Suite**: Provides baselines for regression detection
- **Load Balancer**: Concurrency analysis informs distribution strategies
