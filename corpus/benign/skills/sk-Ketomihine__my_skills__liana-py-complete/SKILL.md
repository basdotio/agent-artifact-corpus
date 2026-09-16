---
name: liana-py-complete
description: Liana-py 细胞互作分析工具包 - 100%覆盖文档（60个核心文件+72个图片文件）
---

# Liana-Py-Complete Skill

Comprehensive assistance with LIANA+ cell-cell communication analysis framework for single-cell, spatially-resolved, and multi-modal omics data.

## When to Use This Skill

This skill should be triggered when:

### Data Analysis Tasks
- **Analyzing single-cell RNA-seq data** for ligand-receptor interactions
- **Processing spatially-resolved transcriptomics data** with spatial coordinates
- **Working with multi-modal omics data** (e.g., CITE-seq, metabolite data)
- **Performing cell-cell communication inference** across different conditions
- **Running differential expression analysis** for communication networks
- **Building spatial neighborhood relationships** between cells/spots

### Specific LIANA+ Features
- **Using individual CCC methods** (CellPhoneDB, CellChat, NATMI, Connectome, etc.)
- **Running rank aggregation** to combine multiple methods
- **Creating visualizations** (dotplots, tileplots, circle plots)
- **Processing ligand-receptor resources** and custom databases
- **Implementing MISTy models** for spatially-informed multi-view learning
- **Calculating bivariate metrics** for spatial interactions
- **Managing multi-sample data** with tensor-cell2cell or MOFA+
- **Working with metabolite-receptor interactions** via MetalinksDB

### Method Development
- **Comparing different CCC inference methods**
- **Customizing ligand-receptor resources** for specific organisms
- **Implementing spatial analysis workflows**
- **Debugging LIANA+ pipelines** and error handling
- **Optimizing parameters** for communication inference

## Quick Reference

### Core Setup and Data Loading
**Example 1** (Basic imports and setup):
```python
import liana as li
import scanpy as sc
import omnipath as op
import decoupler as dc

# Load example data
adata = sc.datasets.pbmc68k_reduced()
```

**Example 2** (Multi-modal data setup):
```python
import numpy as np
import pandas as pd
import scanpy as sc
import liana as li
import mudata as mu
from matplotlib import pyplot as plt

# Load CITE-seq data
prot = sc.read('citeseq_prot.h5ad')
rna = sc.read('citeseq_rna.h5ad')
```

### Running Cell-Cell Communication Methods
**Example 3** (Individual method - CellPhoneDB):
```python
from liana.method import cellphonedb

cellphonedb(adata,
            groupby='bulk_labels',
            resource_name='consensus',
            expr_prop=0.1,
            verbose=True,
            key_added='cpdb_res')
```

**Example 4** (Rank aggregation across methods):
```python
li.mt.rank_aggregate(adata,
                     groupby='bulk_labels',
                     resource_name='consensus',
                     expr_prop=0.1,
                     verbose=True)
```

### Resource Management
**Example 5** (Working with ligand-receptor resources):
```python
# Show available resources
li.resource.show_resources()

# Select specific resource
resource = li.resource.select_resource('consensus')

# Generate custom LR geneset
lr_progeny = li.resource.generate_lr_geneset(lr_pairs, progeny, lr_sep="^")
```

### Visualization
**Example 6** (Creating dotplots):
```python
li.pl.dotplot(adata=adata,
              colour='lr_means',
              size='cellphone_pvals',
              inverse_size=True,
              source_labels=['CD34+', 'CD56+ NK'],
              target_labels=['CD34+', 'CD56+ NK'],
              filter_fun=lambda x: x['cellphone_pvals'] <= 0.05)
```

**Example 7** (Customizing plots with plotnine):
```python
import plotnine as p9

(my_plot +
 p9.theme_dark() +
 p9.theme(strip_text=p9.element_text(size=11),
          figure_size=(7, 4)))
```

### Spatial and Multi-Modal Analysis
**Example 8** (MISTy models for spatial data):
```python
from liana.method import MistyData, genericMistyData, lrMistyData

# Create and run MISTy model
misty = MistyData(adata, intra_groupby='cell_type', extra_groupby='spatial')
misty.run_model()
```

**Example 9** (Multi-view tensor analysis):
```python
# Convert LIANA results to tensor for cell2cell analysis
tensor = li.multi.to_tensor_c2c(adata,
                                sample_key='sample_id',
                                score_key='magnitude_rank',
                                liana_res=adata.uns['liana_res'])
```

### Utility Functions
**Example 10** (Data transformation):
```python
# Extract obsm to new AnnData
new_adata = li.utils.obsm_to_adata(adata, obsm_key='spatial')

# Handle negative values
positive_data = li.utils.neg_to_zero(data_matrix, cutoff=0)

# Interpolate data to common space
interpolated = li.utils.interpolate_adata(adata1, adata2)
```

## Key Concepts

### Core LIANA+ Components
- **Ligand-Receptor Methods**: Statistical approaches to infer CCC from transcriptomics data
- **Resources**: Prior knowledge databases of ligand-receptor interactions (consensus, CellPhoneDB, etc.)
- **Magnitude Score**: Strength of interaction (e.g., mean expression)
- **Specificity Score**: How specific an interaction is to particular cell type pairs
- **Rank Aggregation**: Combining multiple methods using Robust Rank Aggregation (RRA)

### Data Structures
- **AnnData**: Standard single-cell data structure with `.X`, `.obs`, `.var`, `.uns`
- **MuData**: Multi-modal data structure for multiple omics layers
- **Spatial Connectivities**: Neighborhood relationships between cells/spots

### Analysis Types
- **Steady-state CCC**: Standard ligand-receptor inference from single-cell data
- **Spatially-informed Analysis**: Methods incorporating spatial coordinates
- **Multi-modal Integration**: Analysis across different data modalities
- **Differential Analysis**: Comparing communication across conditions

## Reference Files

This skill includes comprehensive documentation organized in `references/`:

### **api.md** (45 pages)
**Core API documentation for all LIANA+ functions**
- Method signatures and parameters for all CCC inference methods
- Utility functions for data transformation and spatial analysis
- Complete parameter descriptions and return values
- **Best for**: Looking up specific function syntax, parameter details, and usage examples

### **getting_started.md** (4 pages)
**Introduction and decision tree for choosing analysis methods**
- Framework overview and capabilities
- Decision tree for spatial vs non-spatial analysis
- Installation and basic setup instructions
- **Best for**: New users getting started with LIANA+ and choosing appropriate methods

### **tutorials.md** (Comprehensive tutorials)
**Step-by-step walkthroughs of common analyses**
- Steady-state ligand-receptor inference with detailed examples
- Multi-modal data integration workflows
- Spatial analysis and MISTy model implementation
- **Best for**: Learning complete workflows and understanding analysis pipelines

### **other.md** (2 pages)
**Additional information and changelog**
- Version history and new features
- Citation information and acknowledgments
- **Best for**: Checking version compatibility and proper citation

## Working with This Skill

### For Beginners
1. **Start with `getting_started.md`** to understand the framework and choose your analysis approach
2. **Follow the basic tutorials** for steady-state ligand-receptor inference
3. **Use the Quick Reference examples** to get started with common tasks
4. **Focus on individual methods first** before moving to advanced features

### For Intermediate Users
1. **Explore the API documentation** for specific function parameters and advanced options
2. **Try multi-modal analysis** if you have CITE-seq or spatial data
3. **Experiment with different visualization options** to best present your results
4. **Use rank aggregation** to combine multiple methods for more robust results

### For Advanced Users
1. **Customize ligand-receptor resources** for specific organisms or interactions
2. **Implement spatial analysis pipelines** with MISTy models and bivariate metrics
3. **Build multi-sample workflows** using tensor-cell2cell or MOFA+ integration
4. **Optimize parameters** for specific data types and research questions

### Navigation Tips
- **Search by function name** in the API documentation for quick reference
- **Check the tutorials** for complete workflow examples
- **Use the decision tree** in getting_started.md to guide analysis choices
- **Refer to method details** in tutorials for mathematical formulations and assumptions

## Resources

### references/
Organized documentation extracted from official sources. These files contain:
- Detailed explanations of LIANA+ concepts and methods
- Complete code examples with proper syntax highlighting
- Mathematical formulations for statistical methods
- Links to original documentation and citations

### scripts/
Add helper scripts here for common automation tasks such as:
- Batch processing of multiple samples
- Custom visualization functions
- Data preprocessing pipelines

### assets/
Add templates, boilerplate, or example projects here:
- Example analysis notebooks
- Custom resource files
- Configuration files for different analysis types

## Notes

- This skill was generated from official LIANA+ documentation (version 1.6.1)
- Reference files preserve the structure and examples from source documentation
- Code examples are extracted from real tutorials and API documentation
- Mathematical formulations and method details are preserved from original sources
- LIANA+ is part of the scverse ecosystem and integrates with AnnData/MuData objects

## Updating

To refresh this skill with updated documentation:
1. Re-run the scraper with the same configuration
2. The skill will be rebuilt with the latest information from the official LIANA+ documentation

## Key Dependencies

LIANA+ typically works with these complementary packages:
- **scanpy**: Single-cell analysis and data manipulation
- **omnipath**: Access to comprehensive prior knowledge databases
- **decoupler**: Pathway enrichment and transcription factor activity analysis
- **plotnine**: Grammar of graphics plotting in Python
- **mudata**: Multi-modal data structure support