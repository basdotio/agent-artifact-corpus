---
name: envi-pkg-local-improved
description: ENVI spatial transcriptomics analysis toolkit - comprehensive documentation with tutorials and Python source code
---

# Envi-Pkg-Local-Improved Skill

Comprehensive assistance with ENVI (Environmental Niche-aware Variational Integration) spatial transcriptomics analysis, generated from official documentation.

## When to Use This Skill

This skill should be triggered when:

### **Core ENVI Analysis Tasks**
- **Spatial transcriptomics integration** - When working with paired scRNA-seq and spatial data
- **Niche covariance analysis** - When calculating COVET matrices for cellular niches
- **Gene imputation** - When imputing missing genes in spatial transcriptomics data
- **Latent embedding analysis** - When generating and analyzing ENVI latent representations
- **Cell type niche composition** - When analyzing cellular neighborhood composition

### **Data Processing & Visualization**
- **MERFISH data analysis** - When working with Multiplexed Error-Robust Fluorescence In Situ Hybridization data
- **Motor cortex spatial analysis** - When analyzing cortical layer organization and depth
- **UMAP visualization** - When creating dimensionality reduction plots of integrated data
- **Force-directed layouts** - When computing FDL layouts for covariance matrices

### **Technical Implementation**
- **Model training and configuration** - When setting up and training ENVI models
- **CUDA/GPU configuration** - When configuring computational resources for analysis
- **Batch processing** - When handling multiple spatial datasets or batches
- **Utility function implementation** - When implementing diffusion maps, FDL, or other analytical tools

### **Specific Use Cases**
- Predicting spatial context for dissociated scRNA-seq data
- Quantifying cellular niches based on gene-gene covariance
- Analyzing cortical depth and cellular organization
- Integrating multi-modal spatial and single-cell datasets
- Debugging ENVI model convergence or performance issues

## Quick Reference

### **Essential Setup**

**Environment Configuration**
```python
import os
os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"]="0"  # Change to -1 for CPU
import warnings
warnings.filterwarnings('ignore')
```

**Core Imports**
```python
from scenvi.ENVI import ENVI
from scenvi.utils import compute_covet
```

**Data Loading**
```python
import scanpy as sc
st_data = sc.read_h5ad('st_data.h5ad')  # Spatial data
sc_data = sc.read_h5ad('sc_data.h5ad')  # scRNA-seq data
```

### **Model Initialization & Training**

**ENVI Model Setup**
```python
envi_model = scenvi.ENVI(spatial_data=st_data, sc_data=sc_data)
# Output: Computing Niche Covariance Matrices, Initializing VAE
```

**Model Training**
```python
envi_model.train()
envi_model.impute_genes()
envi_model.infer_niche_covet()
envi_model.infer_niche_celltype()
```

### **Data Processing Utilities**

**Force-Directed Layout for COVET Analysis**
```python
def FDL(data, k=30):
    nbrs = sklearn.neighbors.NearestNeighbors(n_neighbors=int(k), metric='euclidean', n_jobs=5).fit(data)
    kNN = nbrs.kneighbors_graph(data, mode='distance')
    # Adaptive kernel computation and layout calculation
    layout = force_directed_layout(kernel)
    return layout
```

**Diffusion Maps Implementation**
```python
def run_diffusion_maps(data_df, n_components=10, knn=30, alpha=0):
    # Adaptive anisotropic kernel computation
    # Markov normalization and eigen decomposition
    return {"T": T, "EigenVectors": V, "EigenValues": D, "kernel": kernel}
```

### **Visualization & Analysis**

**UMAP for Integrated Data**
```python
fit = umap.UMAP(n_neighbors=100, min_dist=0.3, n_components=2)
latent_umap = fit.fit_transform(np.concatenate([st_data.obsm['envi_latent'], sc_data.obsm['envi_latent']], axis=0))
```

**Spatial Visualization with Cell Type Colors**
```python
cell_type_palette = {
    'Astro': (0.843137, 0.0, 0.0, 1.0),
    'L23_IT': (0.007843, 0.533333, 0.0, 1.0),
    'Pvalb': (0.47451, 0.0, 0.0, 1.0),
    # ... complete palette for all cell types
}
```

### **Specialized Analysis**

**COVET Matrix Computation**
```python
# Use the utility function for niche covariance
covet_matrices = compute_covet(
    spatial_data=st_data,
    k=8,
    g=64,
    spatial_key="spatial"
)
```

**Cortical Depth Analysis**
```python
# For specific cell types (e.g., Sst neurons)
st_data_sst = st_data[st_data.obs['cell_type'] == 'Sst']
sc_data_sst = sc_data[sc_data.obs['cell_type'] == 'Sst']
# Run FDL on COVET_SQRT for pseudo-depth prediction
```

## Key Concepts

### **COVET (Cellular Niche Covariance)**
- **Purpose**: Represents and quantifies cellular niches based on gene-gene covariance patterns
- **Input**: Spatial transcriptomics data with physical coordinates
- **Output**: Niche gene-gene covariance matrix for each cell
- **Key Insight**: Distance between COVET matrices is calculated as L2 between their square roots

### **ENVI (Environmental Niche-aware Variational Integration)**
- **Purpose**: Integrates paired scRNA-seq and spatial data using COVET representations
- **Architecture**: Conditional Variational Autoencoder (CVAE) with spatial/scRNA-seq modes
- **Capabilities**:
  - Predicts spatial context for dissociated scRNA-seq data
  - Imputes missing genes for spatial data
  - Generates joint latent embeddings for integrated analysis
  - Produces predicted COVET matrices for scRNA-seq data

### **Analysis Workflow**
1. **Preprocessing**: Configure environment, load spatial and scRNA-seq data
2. **COVET Calculation**: Compute niche covariance matrices for spatial data
3. **Model Training**: Train ENVI CVAE on integrated datasets
4. **Inference**: Generate predictions, imputations, and latent embeddings
5. **Analysis**: Visualize UMAPs, analyze cortical depth, examine niche composition

### **Computational Considerations**
- **GPU Support**: Configure CUDA for accelerated training (use -1 for CPU)
- **Memory Management**: Use batch processing for large datasets
- **Distance Metrics**: COVET analysis uses sqrt-transformed matrices for distance calculations
- **Batch Effects**: Support for batch-aware nearest neighbor computation

## Reference Files

This skill includes comprehensive documentation in `references/`:

### **core_documentation.md**
- **Utilities documentation** - Helper functions and computational tools
- **Search functionality** - Documentation search and navigation
- **Core infrastructure** - Essential framework components

### **getting_started.md**
- **Complete ENVI tutorial** - Step-by-step MERFISH analysis workflow
- **Installation guide** - Package setup and dependency management
- **Data loading examples** - Motor cortex scRNA-seq and MERFISH datasets
- **Visualization techniques** - Spatial plots, UMAPs, and analysis figures
- **Advanced analysis** - COVET analysis, cortical depth prediction, niche composition

### **python_api.md**
- **Complete API reference** - All public functions and classes
- **Configuration options** - Sphinx documentation build configuration
- **Internal modules** - Distribution functions, neural network architectures
- **Utility functions** - Covariance computation, batch processing, niche analysis

## Working with This Skill

### **For Beginners**
1. **Start with getting_started.md** - Contains the complete tutorial with real MERFISH data
2. **Follow the environment setup** - Ensure proper CUDA configuration and package installation
3. **Run the basic workflow** - Data loading → model initialization → training → analysis
4. **Study the visualization examples** - Learn to create spatial plots and UMAPs

### **For Intermediate Users**
1. **Explore python_api.md** - Understand the complete API and customization options
2. **Experiment with utility functions** - Implement custom diffusion maps and FDL layouts
3. **Analyze specific cell types** - Focus on neuronal subtypes and cortical organization
4. **Optimize model parameters** - Adjust k-NN parameters, latent dimensions, and training settings

### **For Advanced Users**
1. **Modify core algorithms** - Customize COVET computation, CVAE architecture, or loss functions
2. **Scale to large datasets** - Implement batch processing and memory optimization
3. **Integrate new modalities** - Adapt ENVI for other spatial transcriptomics platforms
4. **Develop custom analyses** - Create specialized niche metrics or visualization techniques

### **Navigation Tips**
- **Use view command** to read specific reference files for detailed information
- **Search for keywords** like "COVET", "latent", "imputation" to find relevant sections
- **Follow code examples** in order - they build from basic setup to advanced analysis
- **Check function signatures** in python_api.md for parameter options and requirements

## Resources

### **references/**
Organized documentation extracted from official sources containing:
- Detailed conceptual explanations and mathematical foundations
- Complete code examples with proper language annotations
- Step-by-step tutorials with real biological datasets
- Links to original documentation and supplementary materials
- Structured table of contents for rapid navigation

### **scripts/**
Add helper scripts for common automation tasks:
- Batch processing pipelines for multiple datasets
- Custom visualization functions for specific analyses
- Data preprocessing utilities for different spatial platforms

### **assets/**
Add templates and example projects:
- Complete analysis workflows for MERFISH data
- Configuration files for different experimental designs
- Example datasets and expected outputs for testing

## Notes

- **Biological focus**: Originally developed for motor cortex MERFISH analysis but applicable to any spatial transcriptomics data
- **Mathematical foundation**: Based on rigorous covariance-based niche representation and variational inference
- **Computational efficiency**: Supports GPU acceleration and batch processing for large-scale datasets
- **Extensibility**: Modular design allows customization of individual components
- **Quality assurance**: All code examples extracted from working tutorials and tested implementations

## Updating

To refresh this skill with updated documentation:
1. Re-run the documentation scraper with the same configuration
2. The skill will be rebuilt with the latest API changes and examples
3. Existing custom scripts and assets in the skill directory will be preserved
4. Backup copies are automatically created before updates