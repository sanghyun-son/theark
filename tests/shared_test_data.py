"""Shared test data for theark tests."""

# ArXiv Mock Data
ARXIV_RESPONSES = {
    "1706.03762": """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762</id>
    <updated>2017-12-06T00:37:27Z</updated>
    <published>2017-06-12T17:57:58Z</published>
    <title>Attention Is All You Need</title>
    <summary>The dominant sequence transduction models are based on complex recurrent or
convolutional neural networks that include an encoder and a decoder. The best
performing models also connect the encoder and decoder through an attention
mechanism. We propose a new simple network architecture, the Transformer,
based solely on attention mechanisms, dispensing with recurrence and
convolutions entirely.</summary>
    <author>
      <name>Ashish Vaswani</name>
    </author>
    <author>
      <name>Noam Shazeer</name>
    </author>
    <author>
      <name>Niki Parmar</name>
    </author>
    <link href="http://arxiv.org/abs/1706.03762" rel="alternate" type="text/html"/>
    <link title="pdf" href="http://arxiv.org/pdf/1706.03762" rel="related" type="application/pdf"/>
    <arxiv:primary_category xmlns:arxiv="http://arxiv.org/schemas/atom" term="cs.CL" scheme="http://arxiv.org/schemas/atom"/>
    <category term="cs.CL" scheme="http://arxiv.org/schemas/atom"/>
    <category term="cs.AI" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
</feed>""",
    "9999.99999": """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <opensearch:totalResults xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">0</opensearch:totalResults>
  <opensearch:startIndex xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">0</opensearch:startIndex>
  <opensearch:itemsPerPage xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">1</opensearch:itemsPerPage>
</feed>""",
    "default": """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1409.0575</id>
    <updated>2014-09-01T22:29:38Z</updated>
    <published>2014-09-01T22:29:38Z</published>
    <title>ImageNet Large Scale Visual Recognition Challenge</title>
    <summary>The ImageNet Large Scale Visual Recognition Challenge is a benchmark in
object category classification and detection on hundreds of object categories
and millions of images. The challenge has been run annually from 2010 to
present, attracting participation from more than fifty institutions.
  This paper describes the creation of this benchmark dataset and the advances
in object recognition that have been possible as a result. We discuss the
challenges of collecting large-scale ground truth annotation, highlight key
breakthroughs in categorical object recognition, provide a detailed analysis of
the current state of the field of large-scale image classification and object
detection, and compare the state-of-the-art computer vision accuracy with human
accuracy. We conclude with lessons learned in the five years of the challenge,
and propose future directions and improvements.</summary>
    <author>
      <name>Olga Russakovsky</name>
    </author>
    <author>
      <name>Jia Deng</name>
    </author>
    <author>
      <name>Hao Su</name>
    </author>
    <author>
      <name>Jonathan Krause</name>
    </author>
    <author>
      <name>Sanjeev Satheesh</name>
    </author>
    <author>
      <name>Sean Ma</name>
    </author>
    <author>
      <name>Zhiheng Huang</name>
    </author>
    <author>
      <name>Andrej Karpathy</name>
    </author>
    <author>
      <name>Aditya Khosla</name>
    </author>
    <author>
      <name>Michael Bernstein</name>
    </author>
    <author>
      <name>Alexander C. Berg</name>
    </author>
    <author>
      <name>Li Fei-Fei</name>
    </author>
    <link href="http://arxiv.org/abs/1409.0575" rel="alternate" type="text/html"/>
    <link title="pdf" href="http://arxiv.org/pdf/1409.0575" rel="related" type="application/pdf"/>
    <arxiv:primary_category xmlns:arxiv="http://arxiv.org/schemas/atom" term="cs.CV" scheme="http://arxiv.org/schemas/atom"/>
    <category term="cs.CV" scheme="http://arxiv.org/schemas/atom"/>
    <category term="I.4.8; I.5.2" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
</feed>""",
}

# OpenAI Mock Data
OPENAI_RESPONSES = {
    "tool_response": {
        "id": "chatcmpl-test-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "gpt-4o-mini",
        "usage": {
            "prompt_tokens": 150,
            "completion_tokens": 80,
            "total_tokens": 230,
        },
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "type": "function",
                            "function": {
                                "name": "Structure",
                                "arguments": '{"tldr": "This paper presents a novel approach to abstract summarization using professional analysis methods.", "motivation": "Current methods lack structured analysis of research papers and fail to provide relevance scoring.", "method": "The authors propose a function-calling approach with structured output and professional evaluation criteria.", "result": "Improved accuracy in extracting key information from abstracts with relevance scoring from 1-10.", "conclusion": "Function calling enables better structured summarization with professional-grade analysis.", "relevance": "8"}',
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
    },
    "text_response": {
        "id": "chatcmpl-test-456",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "gpt-4o-mini",
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 20,
            "total_tokens": 70,
        },
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This paper presents a professional analysis of abstract summarization methods. The research demonstrates improved techniques for extracting key information with relevance scoring. Based on the provided interests, this work has a relevance score of 7 out of 10.",
                },
                "finish_reason": "stop",
            }
        ],
    },
    "batch_response": {
        "id": "batch-test-123",
        "object": "batch",
        "status": "completed",
        "results": [
            {
                "custom_id": "paper-001",
                "response": {
                    "status_code": 200,
                    "body": {
                        "id": "chatcmpl-batch-1",
                        "object": "chat.completion",
                        "created": 1677652288,
                        "model": "gpt-4o-mini",
                        "choices": [
                            {
                                "index": 0,
                                "message": {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [
                                        {
                                            "id": "call_batch_1",
                                            "type": "function",
                                            "function": {
                                                "name": "Structure",
                                                "arguments": '{"tldr": "Batch processed paper summary.", "motivation": "Efficient processing of multiple papers.", "method": "Batch API processing.", "result": "Successfully processed in batch.", "conclusion": "Batch processing is effective.", "relevance": "Medium"}',
                                            },
                                        }
                                    ],
                                },
                                "finish_reason": "tool_calls",
                            }
                        ],
                        "usage": {
                            "prompt_tokens": 30,
                            "completion_tokens": 15,
                            "total_tokens": 45,
                        },
                    },
                },
            }
        ],
    },
}
