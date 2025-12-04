from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate
from langchain.chat_models import init_chat_model
from practicepreach.rag import Rag

tone_analysis_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert at analyzing political texts and comparing their tone and style.
Your task is to analyze how the tone differs between party manifestos and parliamentary speeches on the same topic.

Analyze:
- Tone differences (formal vs. informal, assertive vs. cautious, etc.)
- Language style (academic vs. conversational, abstract vs. concrete)
- Rhetorical strategies (promises vs. explanations, vision vs. reality)
- Emotional register (passionate vs. measured, optimistic vs. pragmatic)
- Level of detail and specificity
- Use of technical vs. accessible language
- Coverage of topics: Are the same topics covered in speech as they are in manifestos

Take into account that a manifesto is always written and speeches are spoken. Therefore the baseline language is different.
Please judge if the speech reflects well, what the party promised to do. Give only one of these labels:
'Does not align well with manifesto', 'Aligns partly with manifesto', 'Aligns mostly with manifesto', 'Aligns well with manifesto'.

"""),
    ("human", """Compare following manifesto excerpts and parliamentary speeches:

MANIFESTO EXCERPTS:
{manifesto_texts}

PARLIAMENTARY SPEECHES:
{speech_texts}

Give me an alignment label. Only one and without explanation.""")
])




def extract_texts_from_chunks(chunks: list) -> str:
    """Extract and combine page_content from chunks."""
    texts = []
    for i, chunk in enumerate(chunks):
        if isinstance(chunk, dict) and 'page_content' in chunk:
            texts.append(f"[Excerpt {i+1}]\n{chunk['page_content']}")
    return "\n\n---\n\n".join(texts)


def analyze_tone_differences(
    manifesto: str,
    speech: str,
    model
) -> dict:
    """
    Analyze tone differences between manifesto and speech chunks from JSON files.

    Args:
        manifesto_json_path: Path to JSON file containing manifesto chunks
        speech_json_path: Path to JSON file containing speech chunks
        topic: Topic being analyzed

    Returns:
        Dictionary with analysis results
    """

    # Create prompt
    prompt = tone_analysis_prompt.invoke({
        "manifesto_texts": manifesto,
        "speech_texts": speech
    })

    # Get analysis from LLM
    print("\nScoring alignment with LLM...")
    response = model.invoke(prompt)

    return  response.content


if __name__ == "__main__":
    # Use the climate query JSON files
    data_dir = Path("data")
    manifesto_json = data_dir / "m_climate_query_CDUCSU.json"
    speech_json = data_dir / "s_climate_query_CDUCSU.json"

    if not manifesto_json.exists():
        print(f"Error: Manifesto JSON not found: {manifesto_json}")
    elif not speech_json.exists():
        print(f"Error: Speech JSON not found: {speech_json}")
    else:
        analysis = analyze_tone_differences(
            str(manifesto_json),
            str(speech_json),
        )

        print("\n" + "="*60)
        print("TONE ANALYSIS")
        print("="*60)
        print(f"Manifesto chunks analyzed: {analysis['manifesto_chunks_count']}")
        print(f"Speech chunks analyzed: {analysis['speech_chunks_count']}")
        print("\n" + "-"*60)
        print("ANALYSIS:")
        print("-"*60)
        print(analysis['tone_analysis'])
