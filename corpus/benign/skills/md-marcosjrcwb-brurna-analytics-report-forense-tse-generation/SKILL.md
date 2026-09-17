---
name: Report Generation
description: Automated generation of technical and legal reports from electoral analysis data. Supports national consolidation and per-state breakdowns.
---

# SKILL: Report Generation (Geração de Relatórios Técnicos)

## Objetivo
Gerar relatórios técnicos profissionais (PDF/Docx) a partir dos dados do `analysis_results.csv`, com fundamentação jurídica fornecida pelo agente **TSE Justice**.

## Estrutura de Relatórios

### Tipos de Relatório

#### 1. Relatório Nacional (Consolidado)
**Escopo**: Análise agregada de todos os estados (AC, AP, RR, TO, SE).
**Seções**:
- Sumário Executivo
- Metodologia
- Resultados Agregados (500 Hipóteses)
- Anomalias Detectadas (Nacional)
- Parecer Jurídico Consolidado
- Recomendações Gerais

#### 2. Relatório por UF
**Escopo**: Análise específica de um estado.
**Seções**:
- Contexto Local (População, Seções, Comparecimento)
- Resultados Específicos da UF
- Comparação com Média Nacional
- Anomalias Locais
- Parecer Jurídico Estadual

## Workflow de Geração

### Fase 1: Coleta de Dados
```python
# Pseudocódigo
df_results = pd.read_csv("analysis_results.csv")
df_temporal = query_db("SELECT * FROM temporal_metrics WHERE uf = ?")
df_logs = query_db("SELECT COUNT(*) FROM log_eventos WHERE source_file LIKE ?")
```

### Fase 2: Análise e Agregação
```python
# Métricas Nacionais
total_hipoteses = len(df_results)
cobertura = (df_results['Status'].isin(['PASS','INFO','FAIL']).sum() / 500) * 100
anomalias = df_results[df_results['Status'].str.contains('FAIL')].copy()

# Métricas por UF
for uf in ['AC', 'AP', 'RR', 'TO', 'SE']:
    uf_logs = query_uf_stats(uf)
    uf_anomalias = filter_anomalias_by_uf(anomalias, uf)
```

### Fase 3: Fundamentação Jurídica
```python
# Invocar TSE Justice Agent
parecer = tse_justice.gerar_parecer(
    anomalias=anomalias,
    nivel_gravidade='MEDIA',
    precedentes=['AC 060338495/2018']
)
```

### Fase 4: Renderização
```python
# Opção 1: PDF (via ReportLab ou WeasyPrint)
pdf = generate_pdf(template='relatorio_nacional.html', data=context)

# Opção 2: Docx (via python-docx)
doc = Document()
doc.add_heading('Relatório Técnico Brurna Analytics', 0)
# ... adicionar seções
doc.save('relatorio_nacional.docx')
```

## Templates de Relatório

### Template: Sumário Executivo
```markdown
# SUMÁRIO EXECUTIVO

**Período de Análise**: [Data Inicial] a [Data Final]
**Estados Analisados**: AC, AP, RR, TO, SE
**Total de Seções**: [X]
**Total de Logs Processados**: [Y]

## Principais Achados
- ✅ **Cobertura**: [99.8%] das hipóteses validadas
- ⚠️ **Anomalias**: [N] seções com comportamento atípico
- 📊 **Conformidade**: [%] de conformidade com padrões esperados

## Conclusão Preliminar
[Texto gerado pelo TSE Justice Agent]
```

### Template: Seção de Anomalias
```markdown
## ANOMALIAS DETECTADAS

### Hipótese H464: Isolation Forest (Machine Learning)
**Status**: FAIL (Anomaly Detected)
**Descrição**: Detecção de anomalias via Isolation Forest não aponta fraude sistêmica.
**Observação**: Found 67 outliers > 3 sigma

**Fundamentação Jurídica**:
> Com fulcro no art. 5º da Resolução TSE 23.603/2019, a análise estatística via Machine Learning constitui indício de comportamento atípico, mas não prova material de irregularidade. Recomenda-se auditoria física das urnas identificadas.

**Seções Afetadas**:
| UF | Seção | Volume | Erros | Z-Score |
|---|---|---|---|---|
| AC | 0001 | 450 | 12 | 3.2 |
| ... | ... | ... | ... | ... |

**Recomendação**: Auditoria Complementar (Art. 103 do Código Eleitoral)
```

## Ferramentas e Bibliotecas

### Python Libraries
```python
# Instalação
pip install reportlab python-docx jinja2 weasyprint

# Imports
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from docx import Document
from jinja2 import Template
```

### Estrutura de Arquivos
```
src/
  reports/
    __init__.py
    generator.py          # Classe principal ReportGenerator
    templates/
      nacional.html       # Template HTML para PDF
      uf.html            # Template por estado
      parecer.html       # Template de parecer jurídico
    assets/
      logo_tse.png       # Logo oficial (se autorizado)
      styles.css         # Estilos para PDF
```

## Implementação: ReportGenerator

### Classe Principal
```python
class ReportGenerator:
    def __init__(self, db_engine, tse_justice_agent):
        self.engine = db_engine
        self.justice = tse_justice_agent
        
    def generate_national_report(self, output_path='relatorio_nacional.pdf'):
        """Gera relatório consolidado nacional"""
        data = self._collect_national_data()
        parecer = self.justice.gerar_parecer(data['anomalias'])
        
        context = {
            'data': data,
            'parecer': parecer,
            'timestamp': datetime.now()
        }
        
        return self._render_pdf('nacional.html', context, output_path)
    
    def generate_uf_report(self, uf, output_path=None):
        """Gera relatório específico de UF"""
        if output_path is None:
            output_path = f'relatorio_{uf}.pdf'
            
        data = self._collect_uf_data(uf)
        parecer = self.justice.gerar_parecer_uf(uf, data['anomalias'])
        
        context = {
            'uf': uf,
            'data': data,
            'parecer': parecer,
            'comparacao_nacional': self._compare_to_national(uf, data)
        }
        
        return self._render_pdf('uf.html', context, output_path)
```

## Casos de Uso

### Uso 1: Relatório Rápido (CLI)
```bash
# Gerar relatório nacional
python -m src.reports.generator --tipo nacional --output relatorio.pdf

# Gerar relatório por UF
python -m src.reports.generator --tipo uf --uf AC --output relatorio_ac.pdf
```

### Uso 2: Integração com Dashboard
```python
# No Streamlit
if st.button("📄 Gerar Relatório Nacional"):
    generator = ReportGenerator(engine, tse_justice)
    pdf_path = generator.generate_national_report()
    
    with open(pdf_path, 'rb') as f:
        st.download_button(
            label="⬇️ Download PDF",
            data=f,
            file_name="relatorio_nacional.pdf",
            mime="application/pdf"
        )
```

## Checklist de Qualidade

### Antes de Gerar Relatório
- [ ] Ingestão de dados completa (5 estados)
- [ ] `analysis_results.csv` atualizado
- [ ] TSE Justice Agent configurado
- [ ] Templates HTML validados

### Validação do Relatório
- [ ] Todas as seções preenchidas
- [ ] Gráficos renderizados corretamente
- [ ] Fundamentação jurídica presente
- [ ] Assinatura digital (se aplicável)
- [ ] Metadados (autor, data, versão)

## Segurança e Compliance

### Dados Sensíveis
- ❌ Não incluir dados de eleitores individuais
- ❌ Não incluir correlação voto-eleitor
- ✅ Apenas dados agregados por seção

### Disclaimer Legal
Todo relatório deve incluir:
```
AVISO LEGAL: Este relatório é gerado por sistema automatizado de análise estatística 
e não substitui perícia oficial da Justiça Eleitoral. Os pareceres jurídicos são 
fundamentados em legislação vigente e jurisprudência, mas não constituem decisão 
judicial. Uso restrito para fins de auditoria interna e transparência.
```

## Próximos Passos (Fase 9)
1. Implementar `src/reports/generator.py`
2. Criar templates HTML (nacional + UF)
3. Integrar com TSE Justice Agent
4. Adicionar botão no Dashboard
5. Testar geração com dados reais

---

**Skill Owner**: Backend Specialist + TSE Justice
**Dependencies**: `reportlab`, `python-docx`, `jinja2`
**Status**: Ready for Implementation
