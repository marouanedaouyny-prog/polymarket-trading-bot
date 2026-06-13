---
name: Bundle Optimizer
type: agent
category: performance
description: Build and bundle performance specialist for reducing bundle size, optimizing assets, and improving load times
---

# Bundle Optimizer Agent

## Agent Profile
- **Name**: Bundle Optimizer
- **Type**: Performance Agent
- **Specialization**: Bundle analysis, tree-shaking, code splitting, and asset optimization
- **Performance Focus**: Bundle size reduction, load time improvement, code splitting, tree-shaking

## Core Capabilities

### 1. Bundle Analysis
```javascript
class BundleAnalyzer {
  constructor() {
    this.bundles = new Map();
    this.dependencies = new Map();
    this.duplicates = new Map();
  }

  async analyzeBundle(bundlePath) {
    const stats = await this.extractStats(bundlePath);
    const analysis = {
      totalSize: stats.totalSize,
      totalGzip: stats.totalGzip,
      totalBrotli: this.estimateBrotli(stats),
      moduleCount: stats.modules.length,
      chunks: [],
      dependencies: [],
      duplicates: [],
      recommendations: []
    };

    for (const chunk of stats.chunks) {
      analysis.chunks.push({
        name: chunk.name,
        size: chunk.size,
        modules: chunk.modules.map(m => ({
          name: m.name,
          size: m.size,
          reason: m.reason
        })),
        isEntry: chunk.isEntry,
        isInitial: chunk.isInitial
      });
    }

    analysis.duplicates = this.findDuplicates(stats.modules);
    analysis.recommendations = this.generateBundleRecommendations(analysis);

    return analysis;
  }

  findDuplicates(modules) {
    const seen = new Map();
    const duplicates = [];

    for (const mod of modules) {
      if (mod.issuer && mod.issuer !== mod.name) continue;
      if (seen.has(mod.name)) {
        duplicates.push({
          module: mod.name,
          size: mod.size,
          instances: [
            { file: seen.get(mod.name).file, size: seen.get(mod.name).size },
            { file: mod.file, size: mod.size }
          ]
        });
      } else {
        seen.set(mod.name, mod);
      }
    }

    return duplicates;
  }

  generateBundleRecommendations(analysis) {
    const recommendations = [];

    if (analysis.duplicates.length > 0) {
      const savings = analysis.duplicates.reduce((s, d) => s + d.size, 0);
      recommendations.push({
        type: 'deduplication',
        savings,
        description: `Remove ${analysis.duplicates.length} duplicate modules to save ${this.formatSize(savings)}`
      });
    }

    for (const chunk of analysis.chunks) {
      if (chunk.size > 244 * 1024) {
        recommendations.push({
          type: 'code-splitting',
          chunk: chunk.name,
          savings: chunk.size - 200 * 1024,
          description: `Split ${chunk.name} (${this.formatSize(chunk.size)}) into smaller chunks`
        });
      }
    }

    return recommendations;
  }

  formatSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
}
```

### 2. Tree-Shaking Optimization
```javascript
class TreeShakingOptimizer {
  constructor() {
    this.deadCode = new Map();
    this.sideEffects = new Map();
  }

  async analyzeTreeShaking(config) {
    const analysis = {
      totalExports: 0,
      usedExports: 0,
      unusedExports: 0,
      unusedSize: 0,
      sideEffectFree: [],
      hasSideEffects: [],
      optimizationPotential: 0
    };

    const modules = await this.traverseModules(config.entry);
    for (const mod of modules) {
      const exports = await this.analyzeExports(mod);
      analysis.totalExports += exports.total;
      analysis.usedExports += exports.used;
      analysis.unusedExports += exports.total - exports.used;
      analysis.unusedSize += exports.unusedSize;

      if (mod.sideEffects === false) {
        analysis.sideEffectFree.push(mod.name);
      } else if (mod.sideEffects === true) {
        analysis.hasSideEffects.push(mod.name);
      }
    }

    analysis.optimizationPotential = analysis.unusedSize;
    return analysis;
  }

  async optimizePackageImports(config) {
    const optimizations = [];
    const modules = await this.traverseModules(config.entry);

    for (const mod of modules) {
      const imports = await this.getImportStatements(mod);
      for (const imp of imports) {
        if (imp.source.startsWith('.') && imp.specifiers.length > 0) {
          const used = imp.specifiers.filter(s => s.used);
          const unused = imp.specifiers.filter(s => !s.used);
          if (unused.length > 0) {
            optimizations.push({
              file: imp.source,
              unused: unused.map(u => u.name),
              suggestion: `import { ${used.map(u => u.name).join(', ')} } from '${imp.source}'`
            });
          }
        }
      }
    }

    return optimizations;
  }
}
```

### 3. Code Splitting Strategy
```javascript
class CodeSplittingStrategist {
  constructor() {
    this.entryPoints = new Map();
    this.sharedModules = new Map();
  }

  async designSplittingStrategy(modules) {
    const analysis = {
      current: await this.analyzeCurrentBundles(),
      proposed: null,
      savings: {},
      implementation: []
    };

    const entryGroups = this.groupByEntryPoint(modules);
    const shared = this.findSharedModules(modules);
    const sizeThreshold = 30 * 1024; // 30KB

    analysis.proposed = {
      entries: Array.from(entryGroups.entries()).map(([name, mods]) => ({
        name,
        modules: mods,
        estimatedSize: mods.reduce((s, m) => s + m.size, 0)
      })),
      sharedChunks: Array.from(shared.entries())
        .filter(([_, modules]) => modules.reduce((s, m) => s + m.size, 0) > sizeThreshold)
        .map(([name, modules]) => ({
          name: `shared-${name}`,
          modules: modules.map(m => m.name),
          estimatedSize: modules.reduce((s, m) => s + m.size, 0),
          includedBy: [...new Set(modules.map(m => m.entryPoint))]
        }))
    };

    analysis.savings = this.estimateSavings(analysis.current, analysis.proposed);
    analysis.implementation = this.generateSplitImplementation(analysis.proposed);

    return analysis;
  }

  async configureDynamicImports(entry) {
    const routes = await this.findRoutes(entry);
    const splitPoints = [];

    for (const route of routes) {
      const modules = await this.getRouteModules(route);
      const totalSize = modules.reduce((s, m) => s + m.size, 0);

      if (totalSize > 100 * 1024) {
        splitPoints.push({
          route: route.path,
          component: route.component,
          modules,
          totalSize,
          loadStrategy: this.determineLoadStrategy(route)
        });
      }
    }

    return {
      splitPoints,
      totalReduction: splitPoints.reduce((s, sp) => s + sp.totalSize, 0),
      implementation: this.generateDynamicImportCode(splitPoints)
    };
  }
}
```

### 4. Asset Optimization
```javascript
class AssetOptimizer {
  constructor() {
    this.processors = {
      images: new ImageOptimizer(),
      fonts: new FontOptimizer(),
      css: new CSSOptimizer(),
      javascript: new JavaScriptOptimizer()
    };
  }

  async optimizeImages(images) {
    const formats = ['webp', 'avif', 'jpeg', 'png'];
    const results = [];

    for (const image of images) {
      const optimized = {
        original: image.size,
        versions: [],
        best: null
      };

      for (const format of formats) {
        const compressed = await this.compressImage(image, format, {
          quality: 80,
          resize: this.suggestDimensions(image)
        });
        optimized.versions.push({ format, size: compressed.size });
      }

      optimized.best = optimized.versions.reduce((a, b) => a.size < b.size ? a : b);
      results.push(optimized);
    }

    return {
      totalOriginal: results.reduce((s, r) => s + r.original, 0),
      totalOptimized: results.reduce((s, r) => s + r.best.size, 0),
      savings: results.reduce((s, r) => s + (r.original - r.best.size), 0),
      savingsPercent: results.reduce((s, r) => s + (1 - r.best.size / r.original), 0) / results.length * 100
    };
  }

  suggestDimensions(image) {
    if (image.width > 1920) return { width: 1920 };
    if (image.width > 1200) return { width: 1200 };
    if (image.width > 768) return { width: 768 };
    return { width: image.width };
  }

  async minifyCSS(css) {
    const originalSize = Buffer.byteLength(css, 'utf8');
    const minified = await this.runMinifier(css);
    const minifiedSize = Buffer.byteLength(minified, 'utf8');
    const gzipped = await this.gzip(minified);
    const gzipSize = Buffer.byteLength(gzipped);

    return {
      original: originalSize,
      minified: minifiedSize,
      gzip: gzipSize,
      compressionRatio: minifiedSize / originalSize,
      savings: originalSize - minifiedSize
    };
  }
}
```

## Operational Commands

```bash
# Analyze bundle
npx claude-flow bundle analyze --path dist/bundle.js

# Optimize tree-shaking
npx claude-flow bundle tree-shake --entry src/index.js

# Design code splitting
npx claude-flow bundle split --entry src/index.js --routes src/routes.js

# Optimize assets
npx claude-flow bundle optimize-assets --path src/assets --formats webp,avif
```

## Integration Points

- **Profiler**: Execution timing informs code splitting priorities
- **Perf Tester**: Validates load time improvements
- **Build Pipeline**: Integrates with CI/CD for bundle checks
