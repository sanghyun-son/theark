"""Shared test data for theark tests."""

# Sample arXiv XML responses for testing
SAMPLE_PAPER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762</id>
    <updated>2017-06-12T18:00:00Z</updated>
    <published>2017-06-12T18:00:00Z</published>
    <title>Attention Is All You Need</title>
    <summary>We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.</summary>
    <author>
      <name>Ashish Vaswani</name>
    </author>
    <author>
      <name>Noam Shazeer</name>
    </author>
    <author>
      <name>Niki Parmar</name>
    </author>
    <arxiv:primary_category xmlns:arxiv="http://arxiv.org/schemas/atom" term="cs.CL" />
    <category term="cs.CL" />
    <category term="cs.LG" />
    <link title="pdf" href="https://arxiv.org/pdf/1706.03762" rel="related" type="application/pdf" />
    <link title="doi" href="https://doi.org/10.48550/arXiv.1706.03762" rel="related" />
    <arxiv:doi xmlns:arxiv="http://arxiv.org/schemas/atom">10.48550/arXiv.1706.03762</arxiv:doi>
    <arxiv:comment xmlns:arxiv="http://arxiv.org/schemas/atom">NIPS 2017</arxiv:comment>
  </entry>
</feed>"""

EMPTY_FEED_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
</feed>"""

# More detailed XML response (matches mock server format)
DETAILED_PAPER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <title>ArXiv Query: search_query=id:1706.03762&amp;id_list=&amp;start=0&amp;max_results=1</title>
  <id>http://arxiv.org/api/query?search_query=id:1706.03762&amp;id_list=&amp;start=0&amp;max_results=1</id>
  <updated>2023-08-02T00:41:18Z</updated>
  <opensearch:totalResults>1</opensearch:totalResults>
  <opensearch:startIndex>0</opensearch:startIndex>
  <opensearch:itemsPerPage>1</opensearch:itemsPerPage>
  <entry>
    <id>http://arxiv.org/abs/1706.03762</id>
    <updated>2023-08-02T00:41:18Z</updated>
    <published>2017-06-12T17:57:34Z</published>
    <title>Attention Is All You Need</title>
    <summary>The dominant sequence transduction models are based on complex recurrent or convolutional neural networks in an encoder-decoder configuration. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train. Our model achieves 28.4 BLEU on the WMT 2014 English-to-German translation task, improving over the existing best results, including ensembles by over 2 BLEU. On the WMT 2014 English-to-French translation task, our model establishes a new single-model state-of-the-art BLEU score of 41.8 after training for 3.5 days on eight GPUs, a small fraction of the training costs of the best models from the literature. We show that the Transformer generalizes well to other tasks by applying it successfully to English constituency parsing both with large and limited training data.</summary>
    <author>
      <name>Ashish Vaswani</name>
    </author>
    <author>
      <name>Noam Shazeer</name>
    </author>
    <author>
      <name>Niki Parmar</name>
    </author>
    <author>
      <name>Jakob Uszkoreit</name>
    </author>
    <author>
      <name>Llion Jones</name>
    </author>
    <author>
      <name>Aidan N. Gomez</name>
    </author>
    <author>
      <name>Lukasz Kaiser</name>
    </author>
    <author>
      <name>Illia Polosukhin</name>
    </author>
    <link href="http://arxiv.org/abs/1706.03762" rel="alternate" type="text/html"/>
    <link title="pdf" href="http://arxiv.org/pdf/1706.03762" rel="related" type="application/pdf"/>
    <arxiv:primary_category xmlns:arxiv="http://arxiv.org/schemas/atom" term="cs.CL" scheme="http://arxiv.org/schemas/atom"/>
    <category term="cs.CL"/>
    <category term="cs.LG"/>
    <arxiv:doi xmlns:arxiv="http://arxiv.org/schemas/atom">10.48550/arXiv.1706.03762</arxiv:doi>
    <arxiv:journal_ref xmlns:arxiv="http://arxiv.org/schemas/atom"></arxiv:journal_ref>
    <arxiv:comment xmlns:arxiv="http://arxiv.org/schemas/atom">15 pages, 5 figures</arxiv:comment>
  </entry>
</feed>"""

# Sample paper data
SAMPLE_PAPER_DATA = {
    "arxiv_id": "1706.03762",
    "title": "Attention Is All You Need",
    "abstract": "We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.",
    "authors": "Ashish Vaswani;Noam Shazeer;Niki Parmar",
    "primary_category": "cs.CL",
    "categories": "cs.CL,cs.LG",
    "url_abs": "https://arxiv.org/abs/1706.03762",
    "url_pdf": "https://arxiv.org/pdf/1706.03762",
    "published_at": "2017-06-12T18:00:00Z",
    "updated_at": "2017-06-12T18:00:00Z",
}

# Sample summary data
SAMPLE_SUMMARY_DATA = {
    "paper_id": 1,
    "version": 1,
    "overview": "This paper presents the Transformer architecture as a novel approach to sequence-to-sequence modeling.",
    "motivation": "Existing models rely heavily on recurrent or convolutional neural networks which are slow and difficult to parallelize.",
    "method": "The authors propose a model based entirely on attention mechanisms, eliminating recurrence and convolutions.",
    "result": "The Transformer achieves new state-of-the-art results on machine translation tasks while being more parallelizable.",
    "conclusion": "Attention is all you need for sequence modeling, opening up new possibilities for parallelization and efficiency.",
    "language": "English",
    "interests": "attention,transformer,machine translation,neural networks",
    "relevance": 9,
    "model": "gpt-4",
}

# Sample user data
SAMPLE_USER_DATA = {
    "email": "researcher@example.com",
    "display_name": "AI Researcher",
}

# Sample interest data
SAMPLE_INTEREST_DATA = {
    "user_id": 1,
    "kind": "category",
    "value": "cs.CL",
    "weight": 2.0,
}

# Sample star data
SAMPLE_STAR_DATA = {
    "user_id": 1,
    "paper_id": 1,
    "note": "Important paper for my research",
}

# Sample feed item data
SAMPLE_FEED_ITEM_DATA = {
    "user_id": 1,
    "paper_id": 1,
    "score": 0.95,
    "feed_date": "2021-01-01",
}

# Sample crawl event data
SAMPLE_CRAWL_EVENT_DATA = {
    "arxiv_id": "1706.03762",
    "event_type": "FOUND",
    "detail": "Paper found during crawl",
}
