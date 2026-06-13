---
name: Perf Tester
type: agent
category: performance
description: Load, stress, endurance, and spike testing specialist for system performance validation
---

# Performance Tester Agent

## Agent Profile
- **Name**: Perf Tester
- **Type**: Performance Agent
- **Specialization**: Performance testing and validation
- **Performance Focus**: Load testing, stress testing, endurance testing, spike testing, soak testing

## Core Capabilities

### 1. Load Test Engine
```javascript
class LoadTestEngine {
  constructor() {
    this.virtualUsers = new Map();
    this.scenarios = new Map();
    this.collector = new MetricsCollector();
  }

  async executeLoadTest(config) {
    const test = {
      id: this.generateId(),
      config,
      phases: [],
      metrics: {},
      startTime: Date.now()
    };

    // Ramp-up phase
    const rampUp = await this.rampUp(config.rampUp);
    test.phases.push({ name: 'ramp-up', ...rampUp });

    // Sustained load phase
    const sustained = await this.sustainedLoad(config.sustained);
    test.phases.push({ name: 'sustained', ...sustained });

    // Ramp-down phase
    const rampDown = await this.rampDown(config.rampDown);
    test.phases.push({ name: 'ramp-down', ...rampDown });

    test.duration = Date.now() - test.startTime;
    test.metrics = this.aggregateMetrics(test.phases);
    test.passed = this.evaluatePassFail(test.metrics, config.thresholds);

    return test;
  }

  async rampUp(config) {
    const { from, to, duration } = config;
    const stepSize = (to - from) / (duration / 1000);

    for (let users = from; users <= to; users += stepSize) {
      await this.setVirtualUsers(Math.round(users));
      await this.sleep(1000);
    }

    return { users: to, duration: duration };
  }

  async sustainedLoad(config) {
    const { users, duration } = config;
    await this.setVirtualUsers(users);
    await this.sleep(duration);
    return { users, duration };
  }

  aggregateMetrics(phases) {
    const allMetrics = phases.flatMap(p => p.metrics || []);
    return {
      throughput: allMetrics.reduce((s, m) => s + m.throughput, 0) / allMetrics.length,
      avgLatency: allMetrics.reduce((s, m) => s + m.avgLatency, 0) / allMetrics.length,
      p95Latency: this.percentile(allMetrics.map(m => m.p95Latency), 95),
      errorRate: allMetrics.reduce((s, m) => s + m.errors, 0) / allMetrics.reduce((s, m) => s + m.requests, 0),
      totalRequests: allMetrics.reduce((s, m) => s + m.requests, 0)
    };
  }
}
```

### 2. Stress Test Suite
```javascript
class StressTestSuite {
  constructor() {
    this.breakingPoint = null;
    this.degradationCurve = [];
  }

  async findBreakingPoint(config) {
    const { startLoad, maxLoad, increment, duration } = config;
    let currentLoad = startLoad;
    const results = [];

    while (currentLoad <= maxLoad) {
      const phaseResult = await this.applyLoad(currentLoad, duration);
      results.push({
        load: currentLoad,
        ...phaseResult
      });

      if (this.isBreaking(phaseResult)) {
        this.breakingPoint = { load: currentLoad, ...phaseResult };
        break;
      }

      currentLoad += increment;
    }

    return {
      breakingPoint: this.breakingPoint,
      degradationCurve: results,
      maxSustainableLoad: this.findMaxSustainable(results),
      recommendations: this.generateStressRecommendations(results)
    };
  }

  isBreaking(result) {
    return (
      result.errorRate > 0.1 ||
      result.avgLatency > result.baselineLatency * 10 ||
      result.throughput < result.baselineThroughput * 0.1
    );
  }

  findMaxSustainable(results) {
    for (const r of results) {
      if (r.errorRate > 0.01 || r.avgLatency > r.baselineLatency * 3) {
        return r;
      }
    }
    return results[results.length - 1];
  }
}
```

### 3. Endurance & Soak Testing
```javascript
class SoakTester {
  constructor() {
    this.leakDetector = new ResourceLeakDetector();
    this.degradationTracker = new DegradationTracker();
  }

  async soakTest(config) {
    const { users, duration, interval } = config;
    const checkpoints = [];

    await this.startLoad(users);
    const startTime = Date.now();
    let elapsed = 0;

    while (elapsed < duration) {
      await this.sleep(interval);
      elapsed = Date.now() - startTime;

      const checkpoint = {
        timestamp: elapsed,
        performance: await this.measurePerformance(),
        resources: await this.measureResourceUsage(),
        leaks: await this.leakDetector.check()
      };

      checkpoints.push(checkpoint);

      if (this.detectsDegradation(checkpoints)) {
        return {
          status: 'degraded',
          degradedAt: elapsed,
          checkpoints,
          recommendations: this.generateDegradationRecommendations(checkpoints)
        };
      }
    }

    return {
      status: 'passed',
      checkpoints,
      leakReport: this.leakDetector.getReport(),
      summary: this.generateSummary(checkpoints)
    };
  }

  detectsDegradation(checkpoints) {
    if (checkpoints.length < 5) return false;
    const recent = checkpoints.slice(-5);
    const latencyTrend = recent.map(c => c.performance.avgLatency);
    return this.isMonotonicIncreasing(latencyTrend, 0.1);
  }

  async measureResourceUsage() {
    return {
      cpu: process.cpuUsage(),
      memory: process.memoryUsage(),
      handles: process.resourceUsage(),
      gc: await this.getGCStats()
    };
  }
}
```

### 4. Spike Testing
```javascript
class SpikeTester {
  constructor() {
    this.recoveryMetrics = {};
  }

  async spikeTest(config) {
    const { baseline, spike, spikeDuration, recoveryDuration } = config;

    const baselineMetrics = await this.measureBaseline(baseline);

    const spikeStart = Date.now();
    await this.applySpike(spike, spikeDuration);
    const spikeMetrics = await this.measureMetrics();

    await this.recoveryWait(recoveryDuration);
    const recoveryMetrics = await this.measureMetrics();

    return {
      baseline: baselineMetrics,
      spike: {
        duration: spikeDuration,
        ...spikeMetrics,
        peakLatency: spikeMetrics.p95Latency,
        maxThroughput: spikeMetrics.throughput
      },
      recovery: {
        recovered: this.isRecovered(recoveryMetrics, baselineMetrics),
        timeToRecover: Date.now() - spikeStart - spikeDuration,
        metrics: recoveryMetrics
      },
      passed: (
        spikeMetrics.errorRate < config.maxErrorRate &&
        this.isRecovered(recoveryMetrics, baselineMetrics)
      ),
      recommendations: this.generateSpikeRecommendations({
        spikeMetrics, recoveryMetrics, baselineMetrics
      })
    };
  }

  isRecovered(recovery, baseline) {
    const latencyDiff = Math.abs(recovery.avgLatency - baseline.avgLatency);
    return latencyDiff / baseline.avgLatency < 0.2;
  }
}
```

## Operational Commands

```bash
# Run load test
npx claude-flow perf-test load --users 100 --duration 300

# Find breaking point
npx claude-flow perf-test stress --start 10 --max 1000 --increment 50

# Run soak test
npx claude-flow perf-test soak --users 50 --duration 86400 --interval 5000

# Execute spike test
npx claude-flow perf-test spike --baseline 50 --spike 500 --spike-duration 30
```

## Integration Points

- **Benchmark Suite**: Shares baselines and thresholds
- **Performance Monitor**: Feeds real-time test metrics
- **Latency Engineer**: Provides latency profiles for optimization
