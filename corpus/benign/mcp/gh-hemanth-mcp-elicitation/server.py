from fastmcp import FastMCP, Context
from dataclasses import dataclass
from typing import Literal

mcp = FastMCP(name="MCP Elicitation Server")

@mcp.tool
async def book_doctor_appointment(ctx: Context) -> str:
    """Book a doctor appointment by gathering details step by step."""
    
    # Get patient name
    patient_result = await ctx.elicit("What's the patient's name?", response_type=str)
    if patient_result.action != "accept":
        return "Appointment booking cancelled"
    
    # Get appointment type
    appointment_type_result = await ctx.elicit(
        "What type of appointment?", 
        response_type=Literal["consultation", "checkup", "follow-up", "urgent"]
    )
    if appointment_type_result.action != "accept":
        return "Appointment booking cancelled"
    
    # Get preferred time
    time_result = await ctx.elicit("Preferred appointment duration in minutes?", response_type=int)
    if time_result.action != "accept":
        return "Appointment booking cancelled"
    
    # Get insurance info
    insurance_result = await ctx.elicit(
        "Do you have insurance?", 
        response_type=Literal["yes", "no"]
    )
    if insurance_result.action != "accept":
        return "Appointment booking cancelled"
    
    has_insurance = insurance_result.data == "yes"
    return f"Doctor appointment booked for {patient_result.data} - {appointment_type_result.data} ({time_result.data} minutes, Insurance: {has_insurance})"

# 5. Make the server runnable
if __name__ == "__main__":
    import sys
    port = 8001 if "--port" in sys.argv and "8001" in sys.argv else 8000
    mcp.run(transport="http", port=port)