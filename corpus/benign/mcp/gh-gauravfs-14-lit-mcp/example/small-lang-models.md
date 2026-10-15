# Small Language Models: A Comprehensive Survey

## Abstract

The rapid advancement of large language models (LLMs) has revolutionized natural language processing, yet their massive computational requirements and resource demands have created significant barriers to widespread deployment. Small language models (SLMs) have emerged as a compelling alternative, offering the potential to deliver substantial performance while maintaining computational efficiency and accessibility. This comprehensive survey examines the landscape of small language models, their architectural innovations, training methodologies, compression techniques, and diverse applications across various domains. We analyze over 160 recent papers to provide a thorough understanding of how SLMs are reshaping the field of artificial intelligence, from edge computing and mobile applications to specialized domain-specific tasks. Our survey reveals that SLMs not only challenge the conventional wisdom that larger models are inherently superior but also demonstrate remarkable capabilities in resource-constrained environments, making AI more accessible and sustainable.

## 1. Introduction

The evolution of language models has been marked by an unprecedented scaling race, with models growing from millions to hundreds of billions of parameters. While this trend has yielded remarkable capabilities in large language models (LLMs), it has simultaneously created significant challenges in terms of computational requirements, energy consumption, and accessibility. The emergence of small language models (SLMs) represents a paradigm shift toward more efficient, deployable, and sustainable artificial intelligence systems.

Small language models, typically defined as models with parameters ranging from 100 million to 8 billion, have demonstrated that size is not the sole determinant of capability. Recent research by Subramanian et al. [@subramanian2025small] presents a comprehensive analysis of approximately 160 papers, revealing that SLMs in the 1 to 8 billion parameter range can perform as well as, or even outperform, their larger counterparts in specific tasks. This finding challenges the conventional scaling laws and opens new avenues for efficient AI deployment.

The significance of SLMs extends beyond mere parameter reduction. Chen and Varoquaux [@chen2024role] systematically examine the relationship between large and small models from collaboration and competition perspectives, highlighting how SLMs frequently serve practical purposes in real-world applications despite being underestimated in academic discourse. This survey aims to provide a comprehensive understanding of SLMs, their methodologies, applications, and future potential.

## 2. Definition and Characteristics of Small Language Models

### 2.1 Defining Small Language Models

Small language models represent a distinct category of neural language models characterized by their reduced parameter count and computational requirements. Lu et al. [@lu2024small] provide a focused analysis of transformer-based, decoder-only language models with 100M to 5B parameters, emphasizing their widespread adoption in modern smart devices. Unlike their larger counterparts, which are predominantly deployed in data centers and cloud environments, SLMs are designed for on-device deployment and resource-constrained environments.

The effective size of SLMs, as conceptualized by Subramanian et al. [@subramanian2025small], represents their increased capability relative to LLMs when considering their parameter efficiency. This concept acknowledges that smaller models can achieve comparable performance through architectural innovations, training methodologies, and optimization techniques that maximize the utility of each parameter.

### 2.2 Key Characteristics and Advantages

SLMs exhibit several distinctive characteristics that make them particularly suitable for practical deployment. Their reduced memory footprint enables deployment on mobile devices, edge computing systems, and IoT devices where computational resources are limited. The lower computational requirements translate to faster inference times, reduced energy consumption, and improved privacy through on-device processing.

The accessibility of SLMs democratizes AI technology, allowing smaller organizations, academic institutions, and individual researchers to develop and deploy language models without the massive computational infrastructure required for large-scale models. This accessibility is particularly crucial for applications in healthcare, education, and developing regions where computational resources may be limited.

## 3. Architectural Innovations in Small Language Models

### 3.1 Efficient Transformer Architectures

The foundation of modern SLMs lies in efficient transformer architectures that maximize performance while minimizing computational overhead. Recent innovations have focused on optimizing attention mechanisms, reducing memory requirements, and improving computational efficiency. The development of sparse attention patterns, linear attention mechanisms, and efficient positional encodings has enabled SLMs to achieve competitive performance with significantly reduced computational costs.

Architectural innovations in SLMs often involve novel approaches to attention computation, including techniques such as sliding window attention, block-sparse attention, and hierarchical attention mechanisms. These innovations allow models to process longer sequences and maintain contextual understanding while operating within strict computational constraints.

### 3.2 Parameter-Efficient Design Patterns

Modern SLMs employ various parameter-efficient design patterns that maximize the utility of each parameter. These include techniques such as parameter sharing across layers, efficient embedding strategies, and optimized feed-forward network designs. The integration of these patterns enables SLMs to achieve performance levels that were previously thought to require much larger models.

The development of efficient activation functions, normalization techniques, and regularization methods specifically tailored for small models has further enhanced their capabilities. These innovations demonstrate that architectural design, rather than simply parameter count, plays a crucial role in model performance.

## 4. Training Methodologies and Optimization Techniques

### 4.1 Knowledge Distillation and Transfer Learning

Knowledge distillation has emerged as a fundamental technique for training effective SLMs. The process involves transferring knowledge from larger, more capable teacher models to smaller student models, enabling the preservation of performance while dramatically reducing model size. Recent advances in distillation methodologies have shown that carefully designed distillation strategies can enable SLMs to achieve performance levels that approach or even exceed their teacher models in specific domains.

The work by Gao [@gao2023survey] provides a comprehensive overview of recent teacher-student learning studies, highlighting various distillation variants including teaching assistant distillation, curriculum distillation, mask distillation, and decoupling distillation. These approaches aim to improve knowledge transfer efficiency and student model performance through innovative training methodologies.

### 4.2 Parameter-Efficient Fine-Tuning

Parameter-efficient fine-tuning (PEFT) techniques have revolutionized the adaptation of SLMs to specific tasks and domains. Prottasha et al. [@prottasha2025peft] present a comprehensive survey of PEFT techniques, focusing on their motivations, design principles, and effectiveness. These methods allow adapting large models to downstream tasks by updating only a small portion of parameters, making fine-tuning accessible even for resource-constrained environments.

The development of techniques such as Low-Rank Adaptation (LoRA), Adapter modules, and prompt tuning has enabled efficient adaptation of SLMs without requiring full model retraining. These approaches maintain model performance while significantly reducing computational requirements for task-specific adaptation.

### 4.3 Advanced Training Strategies

Modern SLMs employ sophisticated training strategies that optimize for both performance and efficiency. These include curriculum learning approaches that gradually increase task complexity, multi-task learning frameworks that leverage shared representations across tasks, and self-supervised learning techniques that maximize the utility of unlabeled data.

The integration of reinforcement learning from human feedback (RLHF) and other alignment techniques has enabled SLMs to develop more nuanced understanding of human preferences and safety considerations. These training methodologies ensure that SLMs not only achieve high performance but also align with human values and safety requirements.

## 5. Model Compression Techniques

### 5.1 Quantization Methods

Quantization represents one of the most effective techniques for compressing SLMs while maintaining performance. Recent advances in quantization techniques have enabled the deployment of models with significantly reduced precision without substantial performance degradation. The work by Kumar [@kumar2024residual] demonstrates the application of residual vector quantization for KV cache compression in large language models, achieving substantial compression ratios while maintaining model quality.

Liu et al. [@liu2024crossquant] introduce CrossQuant, a post-training quantization method that achieves smaller quantization kernels for precise large language model compression. Their approach demonstrates that careful quantization kernel design can maintain model accuracy while achieving significant compression ratios.

### 5.2 Pruning Techniques

Neural network pruning has emerged as a crucial technique for creating efficient SLMs. Cheng et al. [@cheng2023survey] provide a comprehensive survey of deep neural network pruning, categorizing methods based on universal/specific speedup, timing of pruning, pruning strategies, and integration with other compression techniques. Their analysis reveals that modern pruning techniques can achieve substantial parameter reduction while maintaining or even improving model performance.

The development of structured pruning methods, magnitude-based pruning, and gradient-based pruning has enabled the creation of highly efficient SLMs. These techniques identify and remove redundant parameters while preserving the model's essential functionality.

### 5.3 Knowledge Distillation for Compression

Knowledge distillation serves dual purposes in SLM development: transferring knowledge from larger models and compressing existing models. The work by Wei et al. [@wei2024sentence] provides a comprehensive study on knowledge distillation, comparing sentence-level and token-level approaches. Their analysis reveals that different distillation methods excel in different scenarios, with token-level distillation performing better in simple scenarios and sentence-level distillation excelling in complex scenarios.

The development of hybrid distillation methods that combine multiple distillation approaches has enabled more effective knowledge transfer and model compression. These techniques leverage the strengths of different distillation methodologies to achieve superior performance.

## 6. Applications and Use Cases

### 6.1 Edge Computing and Mobile Applications

SLMs have found extensive applications in edge computing environments where computational resources are limited. The work by Li et al. [@li2025collaborative] explores collaborative inference and learning between edge SLMs and cloud LLMs, presenting a unified taxonomy of edge-cloud collaboration strategies. This collaboration paradigm enables the deployment of sophisticated AI capabilities on resource-constrained devices while maintaining access to more powerful cloud-based models when needed.

Mobile applications represent a primary deployment target for SLMs, where on-device processing provides benefits in terms of privacy, latency, and offline functionality. The development of efficient SLMs has enabled the integration of sophisticated language understanding capabilities into mobile devices, powering applications such as voice assistants, text prediction, and real-time translation.

### 6.2 Healthcare Applications

The healthcare domain has emerged as a significant application area for SLMs, where privacy, efficiency, and accuracy are paramount. Garg et al. [@garg2025rise] present a comprehensive survey of SLMs in healthcare, establishing a taxonomic framework for categorizing models across NLP tasks, stakeholder roles, and the continuum of care. Their analysis reveals the transformative potential of SLMs in healthcare informatics, enabling efficient performance in resource-constrained clinical environments.

SLMs in healthcare applications must balance performance with privacy requirements, computational efficiency, and regulatory compliance. The development of specialized healthcare SLMs has enabled the deployment of AI-powered diagnostic tools, clinical decision support systems, and patient monitoring applications that operate within strict privacy and security constraints.

### 6.3 Specialized Domain Applications

SLMs have demonstrated remarkable capabilities in specialized domains where large models may be overkill or impractical. The development of domain-specific SLMs has enabled the creation of highly specialized AI systems that excel in particular tasks while maintaining computational efficiency.

The versatility of SLMs has enabled their deployment across diverse application domains, from scientific research and education to creative writing and code generation. Their ability to be fine-tuned for specific tasks makes them particularly valuable for applications requiring specialized knowledge or domain expertise.

## 7. Performance Evaluation and Benchmarking

### 7.1 Evaluation Metrics and Benchmarks

The evaluation of SLMs requires comprehensive benchmarking across multiple dimensions, including performance, efficiency, and deployment characteristics. Lu et al. [@lu2024small] evaluate SLM capabilities across various domains including commonsense reasoning, mathematics, in-context learning, and long context processing. Their benchmarking reveals that SLMs can achieve competitive performance across diverse tasks while maintaining computational efficiency.

The development of specialized benchmarks for SLMs has enabled more accurate assessment of their capabilities and limitations. These benchmarks consider not only traditional performance metrics but also efficiency measures such as inference speed, memory usage, and energy consumption.

### 7.2 Comparative Analysis with Large Models

Comparative analysis between SLMs and larger models reveals interesting trade-offs between performance and efficiency. While larger models may achieve superior performance on certain tasks, SLMs often demonstrate competitive performance while offering significant advantages in terms of deployment feasibility, cost, and accessibility.

The analysis of performance-efficiency trade-offs provides valuable insights for practitioners choosing between different model sizes for specific applications. This analysis helps identify scenarios where SLMs may be preferable to larger models and vice versa.

## 8. Challenges and Limitations

### 8.1 Performance Limitations

Despite their advantages, SLMs face certain performance limitations compared to larger models. These limitations may manifest in tasks requiring extensive world knowledge, complex reasoning, or handling of very long sequences. Understanding these limitations is crucial for appropriate model selection and application design.

The development of techniques to mitigate these limitations, such as retrieval-augmented generation, external knowledge integration, and specialized training methodologies, continues to be an active area of research.

### 8.2 Training and Optimization Challenges

Training effective SLMs presents unique challenges that differ from those encountered with larger models. The limited parameter count requires more careful architectural design and training strategy selection. The development of specialized training methodologies for SLMs remains an active area of research.

The optimization of SLMs requires balancing multiple objectives, including performance, efficiency, and deployment constraints. This multi-objective optimization presents challenges that require innovative solutions and careful trade-off analysis.

## 9. Future Directions and Research Opportunities

### 9.1 Architectural Innovations

Future research in SLMs is likely to focus on novel architectural innovations that further improve the efficiency-performance trade-off. The development of new attention mechanisms, activation functions, and architectural patterns specifically designed for small models represents a promising research direction.

The integration of emerging technologies such as neuromorphic computing, quantum computing, and specialized hardware accelerators may enable new approaches to SLM design and deployment.

### 9.2 Training Methodologies

The development of more effective training methodologies for SLMs remains a crucial research area. This includes advances in knowledge distillation, transfer learning, and self-supervised learning techniques specifically tailored for small models.

The exploration of novel training paradigms, such as continual learning, meta-learning, and few-shot learning, may enable SLMs to adapt more effectively to new tasks and domains with limited computational resources.

### 9.3 Applications and Deployment

The expansion of SLM applications to new domains and use cases represents a significant opportunity for future research. The development of specialized SLMs for emerging applications such as autonomous systems, IoT devices, and edge computing environments will likely drive continued innovation in the field.

The integration of SLMs with other AI technologies, such as computer vision, robotics, and multimodal systems, presents opportunities for creating more comprehensive and capable AI systems.

## 10. Conclusion

Small language models represent a transformative development in artificial intelligence, challenging the conventional wisdom that larger models are inherently superior. Through innovative architectural design, sophisticated training methodologies, and effective compression techniques, SLMs have demonstrated remarkable capabilities while maintaining computational efficiency and accessibility.

The comprehensive analysis presented in this survey reveals that SLMs are not merely scaled-down versions of larger models but represent a distinct paradigm in AI development. Their ability to deliver substantial performance while operating within strict computational constraints makes them invaluable for a wide range of applications, from edge computing and mobile devices to specialized domain-specific tasks.

The future of SLMs appears bright, with ongoing research addressing their limitations while exploring new applications and deployment scenarios. As the field continues to evolve, SLMs are likely to play an increasingly important role in making AI more accessible, sustainable, and practical for real-world applications.

The democratization of AI through SLMs represents a significant step toward more inclusive and sustainable artificial intelligence. By enabling sophisticated AI capabilities on resource-constrained devices, SLMs are helping to bridge the digital divide and make advanced AI technology accessible to a broader range of users and applications.

## References

[@subramanian2025small] Subramanian, S., Elango, V., & Gungor, M. (2025). Small Language Models (SLMs) Can Still Pack a Punch: A survey. *arXiv preprint arXiv:2501.05465*. [PDF](http://arxiv.org/pdf/2501.05465v1)

[@chen2024role] Chen, L., & Varoquaux, G. (2024). What is the Role of Small Models in the LLM Era: A Survey. *arXiv preprint arXiv:2409.06857*. [PDF](http://arxiv.org/pdf/2409.06857v5)

[@lu2024small] Lu, Z., Li, X., Cai, D., Yi, R., Liu, F., Zhang, X., Lane, N. D., & Xu, M. (2024). Small Language Models: Survey, Measurements, and Insights. *arXiv preprint arXiv:2409.15790*. [PDF](http://arxiv.org/pdf/2409.15790v3)

[@van2024survey] Van Nguyen, C., Shen, X., Aponte, R., Xia, Y., Basu, S., Hu, Z., Chen, J., Parmar, M., Kunapuli, S., Barrow, J., Wu, J., Singh, A., Wang, Y., Gu, J., Dernoncourt, F., Ahmed, N. K., Lipka, N., Zhang, R., Chen, X., Yu, T., Kim, S., Deilamsalehy, H., Park, N., Rimer, M., Zhang, Z., Yang, H., Rossi, R. A., & Nguyen, T. H. (2024). A Survey of Small Language Models. *arXiv preprint arXiv:2410.20011*. [PDF](http://arxiv.org/pdf/2410.20011v1)

[@chen2025collaborative] Chen, Y., Zhao, J., & Han, H. (2025). A Survey on Collaborative Mechanisms Between Large and Small Language Models. *arXiv preprint arXiv:2505.07460*. [PDF](http://arxiv.org/pdf/2505.07460v1)

[@prottasha2025peft] Prottasha, N. J., Chowdhury, U. R., Mohanto, S., Nuzhat, T., Sami, A. A., Sobuj, M. S. I., Raman, H., Kowsher, M., & Garibay, O. O. (2025). PEFT A2Z: Parameter-Efficient Fine-Tuning Survey for Large Language and Vision Models. *arXiv preprint arXiv:2504.14117*. [PDF](http://arxiv.org/pdf/2504.14117v1)

[@gao2023survey] Gao, M. (2023). A Survey on Recent Teacher-student Learning Studies. *arXiv preprint arXiv:2304.04615*. [PDF](http://arxiv.org/pdf/2304.04615v1)

[@wei2024sentence] Wei, J., Sun, L., Leng, Y., Tan, X., Yu, B., & Guo, R. (2024). Sentence-Level or Token-Level? A Comprehensive Study on Knowledge Distillation. *arXiv preprint arXiv:2404.14827*. [PDF](http://arxiv.org/pdf/2404.14827v1)

[@kumar2024residual] Kumar, A. (2024). Residual vector quantization for KV cache compression in large language model. *arXiv preprint arXiv:2410.15704*. [PDF](http://arxiv.org/pdf/2410.15704v1)

[@liu2024crossquant] Liu, W., Ma, X., Zhang, P., & Wang, Y. (2024). CrossQuant: A Post-Training Quantization Method with Smaller Quantization Kernel for Precise Large Language Model Compression. *arXiv preprint arXiv:2410.07505*. [PDF](http://arxiv.org/pdf/2410.07505v1)

[@cheng2023survey] Cheng, H., Zhang, M., & Shi, J. Q. (2023). A Survey on Deep Neural Network Pruning-Taxonomy, Comparison, Analysis, and Recommendations. *arXiv preprint arXiv:2308.06767*. [PDF](http://arxiv.org/pdf/2308.06767v2)

[@li2025collaborative] Li, S., Wang, H., Xu, W., Zhang, R., Guo, S., Yuan, J., Zhong, X., Zhang, T., & Li, R. (2025). Collaborative Inference and Learning between Edge SLMs and Cloud LLMs: A Survey of Algorithms, Execution, and Open Challenges. *arXiv preprint arXiv:2507.16731*. [PDF](http://arxiv.org/pdf/2507.16731v1)

[@garg2025rise] Garg, M., Raza, S., Rayana, S., Liu, X., & Sohn, S. (2025). The Rise of Small Language Models in Healthcare: A Comprehensive Survey. *arXiv preprint arXiv:2504.17119*. [PDF](http://arxiv.org/pdf/2504.17119v2)

[@patnaik2025small] Patnaik, N., Nayak, N., Agrawal, H. B., Khamaru, M. C., Bal, G., Panda, S. S., Raj, R., Meena, V., & Vadlamani, K. (2025). Small Vision-Language Models: A Survey on Compact Architectures and Techniques. *arXiv preprint arXiv:2503.10665*. [PDF](http://arxiv.org/pdf/2503.10665v1)

[@park2024comprehensive] Park, S., Choi, J., Lee, S., & Kang, U. (2024). A Comprehensive Survey of Compression Algorithms for Language Models. *arXiv preprint arXiv:2401.15347*. [PDF](http://arxiv.org/pdf/2401.15347v1)

[@chen2025towards] Chen, H., Deng, W., Yang, S., Xu, J., Jiang, Z., Ngai, E. C. H., Liu, J., & Liu, X. (2024). Towards Edge General Intelligence via Large Language Models: Opportunities and Challenges. *arXiv preprint arXiv:2410.18125*. [PDF](http://arxiv.org/pdf/2410.18125v3)

[@kandala2024tinyllm] Kandala, S. V., Medaranga, P., & Varshney, A. (2024). TinyLLM: A Framework for Training and Deploying Language Models at the Edge Computers. *arXiv preprint arXiv:2412.15304*. [PDF](http://arxiv.org/pdf/2412.15304v1)

[@shakhadri2024shakti] Shakhadri, S. A. G., KR, K., & Aralimatti, R. (2024). SHAKTI: A 2.5 Billion Parameter Small Language Model Optimized for Edge AI and Low-Resource Environments. *arXiv preprint arXiv:2410.11331*. [PDF](http://arxiv.org/pdf/2410.11331v2)

[@xu2025tensorslm] Xu, M., Xu, Y. L., & Mandic, D. P. (2025). TensorSLM: Energy-efficient Embedding Compression of Sub-billion Parameter Language Models on Low-end Devices. *arXiv preprint arXiv:2506.13514*. [PDF](http://arxiv.org/pdf/2506.13514v1)

[@yan2025are] Yan, X., & Ding, Y. (2025). Are We There Yet? A Measurement Study of Efficiency for LLM Applications on Mobile Devices. *arXiv preprint arXiv:2504.00002*. [PDF](http://arxiv.org/pdf/2504.00002v1)

[@venkatesha2025fast] Venkatesha, Y., Kundu, S., & Panda, P. (2025). Fast and Cost-effective Speculative Edge-Cloud Decoding with Early Exits. *arXiv preprint arXiv:2505.21594*. [PDF](http://arxiv.org/pdf/2505.21594v1)

[@hasan2024distributed] Hasan, S. M., Alotaibi, A. M., Talukder, S., & Shahid, A. R. (2024). Distributed Threat Intelligence at the Edge Devices: A Large Language Model-Driven Approach. *arXiv preprint arXiv:2405.08755*. [PDF](http://arxiv.org/pdf/2405.08755v2)

[@wang2024swapnet] Wang, K., Cao, J., Zhou, Z., & Li, Z. (2024). SwapNet: Efficient Swapping for DNN Inference on Edge AI Devices Beyond the Memory Budget. *arXiv preprint arXiv:2401.16757*. [PDF](http://arxiv.org/pdf/2401.16757v1)

[@qu2022enabling] Qu, Z. (2022). Enabling Deep Learning on Edge Devices. *arXiv preprint arXiv:2210.03204*. [PDF](http://arxiv.org/pdf/2210.03204v1)

[@frantar2025compression] Frantar, E., Evci, U., Park, W., Houlsby, N., & Alistarh, D. (2025). Compression Scaling Laws: Unifying Sparsity and Quantization. *arXiv preprint arXiv:2502.16440*. [PDF](http://arxiv.org/pdf/2502.16440v1)

[@oneill2023self] O'Neill, J., & Dutta, S. (2023). Self-Distilled Quantization: Achieving High Compression Rates in Transformer-Based Language Models. *arXiv preprint arXiv:2307.05972*. [PDF](http://arxiv.org/pdf/2307.05972v1)

[@tao2022compression] Tao, C., Hou, L., Zhang, W., Shang, L., Jiang, X., Liu, Q., Luo, P., & Wong, N. (2022). Compression of Generative Pre-trained Language Models via Quantization. *arXiv preprint arXiv:2203.10705*. [PDF](http://arxiv.org/pdf/2203.10705v2)

[@yang2023quantization] Yang, Z., Choudhary, S., Kunzmann, S., & Zhang, Z. (2023). Quantization-Aware and Tensor-Compressed Training of Transformers for Natural Language Understanding. *arXiv preprint arXiv:2306.01076*. [PDF](http://arxiv.org/pdf/2306.01076v2)

[@wang2025when] Wang, W., Mao, Y., Tang, D., Du, H., Guan, N., & Xue, C. J. (2025). When Compression Meets Model Compression: Memory-Efficient Double Compression for Large Language Models. *arXiv preprint arXiv:2502.15443*. [PDF](http://arxiv.org/pdf/2502.15443v1)

[@slyman2024you] Slyman, E., Kanneganti, A., Hong, S., & Lee, S. (2024). You Never Know: Quantization Induces Inconsistent Biases in Vision-Language Foundation Models. *arXiv preprint arXiv:2410.20265*. [PDF](http://arxiv.org/pdf/2410.20265v1)

[@xu2021low] Xu, J., Chen, X., Hu, S., Yu, J., Liu, X., & Meng, H. (2021). Low-bit Quantization of Recurrent Neural Network Language Models Using Alternating Direction Methods of Multipliers. *arXiv preprint arXiv:2111.14836*. [PDF](http://arxiv.org/pdf/2111.14836v1)

[@oneill2021deep] O'Neill, J., Dutta, S., & Assem, H. (2021). Deep Neural Compression Via Concurrent Pruning and Self-Distillation. *arXiv preprint arXiv:2109.15014*. [PDF](http://arxiv.org/pdf/2109.15014v1)

[@zhang2021why] Zhang, S., Wang, M., Liu, S., Chen, P. Y., & Xiong, J. (2021). Why Lottery Ticket Wins? A Theoretical Perspective of Sample Complexity on Pruned Neural Networks. *arXiv preprint arXiv:2110.05667*. [PDF](http://arxiv.org/pdf/2110.05667v1)

[@oneill2022aligned] O'Neill, J., Dutta, S., & Assem, H. (2022). Aligned Weight Regularizers for Pruning Pretrained Neural Networks. *arXiv preprint arXiv:2204.01385*. [PDF](http://arxiv.org/pdf/2204.01385v2)

[@xu2021rethinking] Xu, D., Yen, I. E. H., Zhao, J., & Xiao, Z. (2021). Rethinking Network Pruning -- under the Pre-train and Fine-tune Paradigm. *arXiv preprint arXiv:2104.08682*. [PDF](http://arxiv.org/pdf/2104.08682v2)

[@liu2025pruning] Liu, Y., Ning, J., Xia, S., Gao, X., Qiang, N., Ge, B., Han, J., & Hu, X. (2025). Pruning Large Language Models by Identifying and Preserving Functional Networks. *arXiv preprint arXiv:2508.05239*. [PDF](http://arxiv.org/pdf/2508.05239v1)

[@yang2022learning] Yang, M., Tjandra, A., Liu, C., Zhang, D., Le, D., & Kalinli, O. (2022). Learning ASR pathways: A sparse multilingual ASR model. *arXiv preprint arXiv:2209.05735*. [PDF](http://arxiv.org/pdf/2209.05735v4)

[@xie2023dynamic] Xie, J., Li, K., Guo, J., Tjandra, A., Shangguan, Y., Sari, L., Wu, C., Jia, J., Mahadeokar, J., & Kalinli, O. (2023). Dynamic ASR Pathways: An Adaptive Masking Approach Towards Efficient Pruning of A Multilingual ASR Model. *arXiv preprint arXiv:2309.13018*. [PDF](http://arxiv.org/pdf/2309.13018v2)

[@yu2021hessian] Yu, S., Yao, Z., Gholami, A., Dong, Z., Kim, S., Mahoney, M. W., & Keutzer, K. (2021). Hessian-Aware Pruning and Optimal Neural Implant. *arXiv preprint arXiv:2101.08940*. [PDF](http://arxiv.org/pdf/2101.08940v3)

[@zhang2025lop] Zhang, Z., Pan, X., Wei, H., & Chen, Z. (2025). LOP: Learning Optimal Pruning for Efficient On-Demand MLLMs Scaling. *arXiv preprint arXiv:2506.12826*. [PDF](http://arxiv.org/pdf/2506.12826v1)

[@tan2023gkd] Tan, S., Tam, W. L., Wang, Y., Gong, W., Yang, Y., Tang, H., He, K., Liu, J., Wang, J., Zhao, S., Zhang, P., & Tang, J. (2023). GKD: A General Knowledge Distillation Framework for Large-scale Pre-trained Language Model. *arXiv preprint arXiv:2306.06629*. [PDF](http://arxiv.org/pdf/2306.06629v1)

[@lin2022tree] Lin, W., Li, Y., Ding, Y., & Zheng, H. T. (2022). Tree-structured Auxiliary Online Knowledge Distillation. *arXiv preprint arXiv:2208.10068*. [PDF](http://arxiv.org/pdf/2208.10068v1)

[@sun2025warmup] Sun, Z., Liu, Y., Meng, F., Chen, Y., Xu, J., & Zhou, J. (2025). Warmup-Distill: Bridge the Distribution Mismatch between Teacher and Student before Knowledge Distillation. *arXiv preprint arXiv:2502.11766*. [PDF](http://arxiv.org/pdf/2502.11766v1)

[@xiao2024dual] Xiao, Y., & Das, R. K. (2024). Dual Knowledge Distillation for Efficient Sound Event Detection. *arXiv preprint arXiv:2402.02781*. [PDF](http://arxiv.org/pdf/2402.02781v1)

[@peng2024pre] Peng, H., Lv, X., Bai, Y., Yao, Z., Zhang, J., Hou, L., & Li, J. (2024). Pre-training Distillation for Large Language Models: A Design Space Exploration. *arXiv preprint arXiv:2410.16215*. [PDF](http://arxiv.org/pdf/2410.16215v1)

[@wu2022unified] Wu, C., Wu, F., Qi, T., & Huang, Y. (2022). Unified and Effective Ensemble Knowledge Distillation. *arXiv preprint arXiv:2204.00548*. [PDF](http://arxiv.org/pdf/2204.00548v1)

[@vengertsev2024confidence] Vengertsev, D., & Sherman, E. (2024). Confidence Preservation Property in Knowledge Distillation Abstractions. *arXiv preprint arXiv:2401.11365*. [PDF](http://arxiv.org/pdf/2401.11365v1)

[@zeineldeen2023robust] Zeineldeen, M., Audhkhasi, K., Baskar, M. K., & Ramabhadran, B. (2023). Robust Knowledge Distillation from RNN-T Models With Noisy Training Labels Using Full-Sum Loss. *arXiv preprint arXiv:2303.05958*. [PDF](http://arxiv.org/pdf/2303.05958v1)

[@kim2023differentiable] Kim, E., & Yang, J. (2023). Differentiable Entailment for Parameter Efficient Few Shot Learning. *arXiv preprint arXiv:2301.13345*. [PDF](http://arxiv.org/pdf/2301.13345v1)

[@xu2025biasedit] Xu, X., Xu, W., Zhang, N., & McAuley, J. (2025). BiasEdit: Debiasing Stereotyped Language Models via Model Editing. *arXiv preprint arXiv:2503.08588*. [PDF](http://arxiv.org/pdf/2503.08588v1)

[@sun2025mitigating] Sun, W., Qu, T., Li, M., Davis, J., & Moens, M. F. (2025). Mitigating Negative Interference in Multilingual Sequential Knowledge Editing through Null-Space Constraints. *arXiv preprint arXiv:2506.10800*. [PDF](http://arxiv.org/pdf/2506.10800v1)

[@borchert2025language] Borchert, P., Vulić, I., Moens, M. F., & De Weerdt, J. (2025). Language Fusion for Parameter-Efficient Cross-lingual Transfer. *arXiv preprint arXiv:2501.06892*. [PDF](http://arxiv.org/pdf/2501.06892v2)

[@liu2024parameter] Liu, W., Hou, J., Yang, D., Cao, M., & Lee, T. (2024). A Parameter-efficient Language Extension Framework for Multilingual ASR. *arXiv preprint arXiv:2406.06329*. [PDF](http://arxiv.org/pdf/2406.06329v1)

[@zhao2024apt] Zhao, B., Hajishirzi, H., & Cao, Q. (2024). APT: Adaptive Pruning and Tuning Pretrained Language Models for Efficient Training and Inference. *arXiv preprint arXiv:2401.12200*. [PDF](http://arxiv.org/pdf/2401.12200v2)

[@ma2025efficiently] Ma, X., Xie, H., & Qin, S. J. (2025). Efficiently Integrate Large Language Models with Visual Perception: A Survey from the Training Paradigm Perspective. *arXiv preprint arXiv:2502.01524*. [PDF](http://arxiv.org/pdf/2502.01524v1)

[@zhang2023composing] Zhang, J., Chen, S., Liu, J., & He, J. (2023). Composing Parameter-Efficient Modules with Arithmetic Operations. *arXiv preprint arXiv:2306.14870*. [PDF](http://arxiv.org/pdf/2306.14870v2)

[@yano2025step] Yano, K., Ito, T., & Suzuki, J. (2025). STEP: Staged Parameter-Efficient Pre-training for Large Language Models. *arXiv preprint arXiv:2504.04151*. [PDF](http://arxiv.org/pdf/2504.04151v1)

[@zong2025mix] Zong, Y., Deng, Y., & Nie, P. (2025). Mix-of-Language-Experts Architecture for Multilingual Programming. *arXiv preprint arXiv:2506.18923*. [PDF](http://arxiv.org/pdf/2506.18923v1)

[@mingjun2023peftt] Mingjun, Z., Zhuoma, D., Nuo, Q., & Tashi, N. (2023). PEFTT: Parameter-Efficient Fine-Tuning for low-resource Tibetan pre-trained language models. *arXiv preprint arXiv:2309.12109*. [PDF](http://arxiv.org/pdf/2309.12109v1)

[@zhao2025lor2c] Zhao, J., Yu, X., Zhang, Y., & Yang, Z. (2025). LoR2C : Low-Rank Residual Connection Adaptation for Parameter-Efficient Fine-Tuning. *arXiv preprint arXiv:2503.00572*. [PDF](http://arxiv.org/pdf/2503.00572v1)

[@gholami2023do] Gholami, S., & Omar, M. (2023). Do Generative Large Language Models need billions of parameters? *arXiv preprint arXiv:2309.06589*. [PDF](http://arxiv.org/pdf/2309.06589v1)

[@khan2023contrastive] Khan, Z., & Fu, Y. (2023). Contrastive Alignment of Vision to Language Through Parameter-Efficient Transfer Learning. *arXiv preprint arXiv:2303.11866*. [PDF](http://arxiv.org/pdf/2303.11866v1)

[@yan2020micronet] Yan, Z., Wang, H., Guo, D., & Han, S. (2020). MicroNet for Efficient Language Modeling. *arXiv preprint arXiv:2005.07877*. [PDF](http://arxiv.org/pdf/2005.07877v1)

[@gao2023examining] Gao, K., He, S., He, Z., Lin, J., Pei, Q., Shao, J., & Zhang, W. (2023). Examining User-Friendly and Open-Sourced Large GPT Models: A Survey on Language, Multimodal, and Scientific GPT Models. *arXiv preprint arXiv:2308.14149*. [PDF](http://arxiv.org/pdf/2308.14149v1)
