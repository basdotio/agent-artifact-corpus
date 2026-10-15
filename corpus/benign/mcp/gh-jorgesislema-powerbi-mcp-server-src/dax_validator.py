"""
Validador de sintaxis DAX
"""
import re
from typing import Dict

class DaxValidator:
    """Valida expresiones DAX sin necesidad de ejecutarlas"""
    
    # Palabras clave de DAX
    KEYWORDS = [
        'CALCULATE', 'FILTER', 'SUM', 'AVERAGE', 'COUNT', 'COUNTROWS',
        'DISTINCT', 'ALL', 'VALUES', 'SELECTEDVALUE', 'IF', 'SWITCH',
        'RELATED', 'USERELATIONSHIP', 'TOTALYTD', 'DATEADD', 'SAMEPERIODLASTYEAR'
    ]
    
    # Funciones comunes
    FUNCTIONS = [
        'SUMX', 'AVERAGEX', 'COUNTX', 'MAXX', 'MINX', 'ADDCOLUMNS',
        'SUMMARIZE', 'GROUPBY', 'NATURALINNERJOIN', 'NATURALLEFTOUTERJOIN'
    ]
    
    @classmethod
    def validate(cls, dax_expression: str) -> Dict:
        """Valida una expresión DAX y retorna resultado"""
        errors = []
        warnings: list[str] = []
        
        if not dax_expression or not dax_expression.strip():
            errors.append("La expresión DAX está vacía")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        # Verificar paréntesis balanceados
        open_parens = dax_expression.count('(')
        close_parens = dax_expression.count(')')
        if open_parens != close_parens:
            errors.append(f"Paréntesis desbalanceados: {open_parens} abiertos, {close_parens} cerrados")
        
        # Verificar corchetes
        open_brackets = dax_expression.count('[')
        close_brackets = dax_expression.count(']')
        if open_brackets != close_brackets:
            errors.append(f"Corchetes desbalanceados: {open_brackets} abiertos, {close_brackets} cerrados")
        
        # Verificar comillas
        if dax_expression.count('"') % 2 != 0:
            errors.append("Comillas dobles desbalanceadas")
        
        if dax_expression.count("'") % 2 != 0:
            warnings.append("Comillas simples pueden estar desbalanceadas (verificar nombres de tablas)")
        
        # Validar keywords en minúscula (warning)
        for kw in cls.KEYWORDS:
            pattern = rf'\b{kw.lower()}\b'
            if re.search(pattern, dax_expression) and kw.lower() not in ['if', 'sum']:
                warnings.append(f"Keyword '{kw}' debería estar en mayúsculas para mejor práctica")
        
        # Verificar posibles errores de sintaxis comunes
        if '= =' in dax_expression:
            errors.append("Operador '= =' inválido. Usar '=' para igualdad")
        
        if '&&&' in dax_expression:
            errors.append("Múltiples operadores AND. Usar '&&'")
        
        if '|||' in dax_expression:
            errors.append("Múltiples operadores OR. Usar '||'")
        
        # Verificar estructura de IF
        if 'IF(' in dax_expression:
            if dax_expression.count('IF(') != dax_expression.count(')'):
                warnings.append("Posible estructura IF incompleta")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "expression_length": len(dax_expression),
            "expression_preview": dax_expression[:100] + "..." if len(dax_expression) > 100 else dax_expression
        }
    
    @classmethod
    def format_dax(cls, dax_expression: str) -> str:
        """Formato básico de DAX (indentación simple)"""
        lines = dax_expression.replace('(', '(\n  ').replace(')', '\n)').split('\n')
        formatted = []
        indent_level = 0
        
        for line in lines:
            indent_level -= line.count(')')
            formatted.append('  ' * max(0, indent_level) + line.strip())
            indent_level += line.count('(')
        
        return '\n'.join(formatted)