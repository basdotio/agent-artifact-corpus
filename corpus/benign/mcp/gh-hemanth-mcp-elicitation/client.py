import asyncio
from fastmcp import Client
from fastmcp.client.elicitation import ElicitResult
from typing import Literal

async def elicitation_handler(message: str, response_type: type, params, context):
    """Enhanced elicitation handler that properly handles different response types."""
    print(f"\n📋 {message}")
    
    try:
        # Try to extract Literal options from the dataclass field annotations
        literal_options = None
        if hasattr(response_type, '__annotations__'):
            for field_name, field_type in response_type.__annotations__.items():
                if hasattr(field_type, '__origin__') and field_type.__origin__ is Literal:
                    literal_options = list(field_type.__args__)
                    break
        
        # If we found Literal options, handle as multiple choice
        if literal_options:
            print(f"📋 Available options: {' | '.join(literal_options)}")
            while True:
                user_input = input(f"👉 Choose one ({'/'.join(literal_options)}): ").strip()
                if not user_input:
                    print("⚠️  Input cannot be empty. Please select an option.")
                    continue
                
                # Case-insensitive matching
                for option in literal_options:
                    if user_input.lower() == option.lower():
                        return response_type(value=option)
                
                print(f"❌ Invalid choice. Please select one of: {' | '.join(literal_options)}")
        
        else:
            # For all other types (str, int, etc.), get input and let response_type handle conversion
            while True:
                try:
                    user_input = input("📝 Enter value: ").strip()
                    if not user_input:
                        print("⚠️  Input cannot be empty. Please enter a value.")
                        continue
                    
                    # Create response using the provided dataclass type
                    return response_type(value=user_input)
                    
                except (ValueError, TypeError) as e:
                    print(f"❌ Invalid input. Please try again.")
                    
    except KeyboardInterrupt:
        print("\n⏹️  Input cancelled.")
        return ElicitResult(action="cancel", content=None)

async def main():
    """Main function to run the client and demonstrate E2E functionality."""
    client = Client(
        "http://127.0.0.1:8000/mcp",
        elicitation_handler=elicitation_handler,
    )
    
    print("🏥 === MCP Doctor Appointment Booking Client ===")
    print("💡 Tip: You can press Ctrl+C at any time to exit\n")
    
    try:
        print("📞 Connecting to MCP server...")
        async with client:
            print("✅ Connected successfully!")
            
            while True:
                try:
                    print("📝 Starting appointment booking process...\n")
                    
                    # Call the book_doctor_appointment tool
                    result = await client.call_tool("book_doctor_appointment")
                    print(f"\n🎉 Appointment booked successfully!")
                    print(f"📋 Booking details: {result}")
                    
                    # Ask if user wants to book another appointment
                    another = input("\n🔄 Would you like to book another appointment? (y/n): ").strip().lower()
                    if another not in ['y', 'yes']:
                        print("👋 Thank you for using the appointment booking system!")
                        break
                    print("\n" + "="*50 + "\n")
                    
                except Exception as e:
                    print(f"\n❌ Error during appointment booking: {type(e).__name__}")
                    print(f"🔍 Details: {e}")
                    
                    retry = input("\n🔄 Would you like to try booking again? (y/n): ").strip().lower()
                    if retry not in ['y', 'yes']:
                        break
                    print("\n" + "="*50 + "\n")
                
    except KeyboardInterrupt:
        print("\n⏹️  Goodbye!")
    except ConnectionError as e:
        print(f"\n🔌 Connection error: Unable to connect to the MCP server")
        print(f"🔍 Details: {e}")
        print("🛠️  Please check that the MCP server is running at http://127.0.0.1:8000/mcp")
    except Exception as e:
        print(f"\n❌ Unexpected error occurred: {type(e).__name__}")
        print(f"🔍 Details: {e}")

if __name__ == "__main__":
    asyncio.run(main())
