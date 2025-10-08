"""
Command Line Interface (CLI) for the AI Analyst agent.

This script allows you to run the agent interactively from the terminal.
It starts the required services, configures the agent, and triggers analysis
by receiving questions from the user.
"""
import traceback

# For these import paths to work, run the project from the root directory
from app.db_analyst.agent import AIAnalyst
from app.db_analyst.llm_service import GeminiService
from app.db_analyst.exceptions import InitializationError, DatabaseConnectionError

def main():
    """Main CLI execution function."""
    print("🤖 SQL Analist Asistanı CLI başlatılıyor...")
    
    try:
        # 1. Create dependencies:
        gemini_service = GeminiService()

        # 2. Create the agent by injecting dependencies:
        analyst = AIAnalyst(gemini_service=gemini_service, db_path="data/chatbot_analytics.db")
        
        print("✅ Asistan hazır. Sorularınızı yazabilirsiniz.")
        print("💡 Çıkmak için 'quit', 'exit', 'q' veya 'çık' yazın.\n")
        
        while True:
            user_query = input("Soru: ").strip()
            
            if user_query.lower() in ['quit', 'exit', 'q', 'çık']: 
                print("👋 Hoşça kalın!")
                break
            
            if not user_query: 
                continue

            print("\n🔍 Analiz başlatılıyor (akış)...")
            final_response = "Analiz tamamlandı ancak nihai bir sonuç üretilemedi."
            
            try:
                # Consume the streaming function in a loop
                for update in analyst.analyze_streaming(user_query):
                    update_type = update.get("type")
                    content = update.get("content")

                    # Print information to the screen according to the type of update received
                    if update_type == "plan":
                        print("🤔 Analiz Planı oluşturuldu:")
                        for i, step in enumerate(content, 1):
                            print(f"   {i}. {step}")
                    elif update_type in ["sql_query", "tool_result", "info"]:
                        # Optionally, you can also show intermediate steps
                        # print(f"   -> {update_type}: {content}")
                        pass # For now, skip intermediate steps
                    elif update_type == "final_result":
                        final_response = content 

                print("\n" + "="*60)
                print("✅ ANALİZ SONUCU:")
                print(final_response)
                print("="*60 + "\n")

            except Exception as e:
                print(f"\n❌ Analiz sırasında bir hata oluştu: {e}")
                traceback.print_exc()

            
    except (InitializationError, DatabaseConnectionError, ValueError) as e:
        print(f"\n❌ Başlatma Hatası: {e}")
    except KeyboardInterrupt:
        print("\n\n👋 Program sonlandırıldı.")
    except Exception as e:
        print(f"\n❌ Beklenmeyen bir hata oluştu: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()