"""Pytest configuration for theark project."""

import pytest
import pytest_asyncio
from pytest_httpserver import HTTPServer

from core import setup_test_logging


@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    """Setup test logging for all tests."""
    setup_test_logging()


@pytest.fixture(scope="function")
def logger():
    """Provide a logger instance for tests."""
    from core import get_logger

    return get_logger("test")


@pytest.fixture(scope="function")
def mock_arxiv_server(httpserver: HTTPServer):
    """Mock arXiv API server for testing."""

    # Realistic paper XML response based on actual arXiv API format
    # Using the structure from https://arxiv.org/abs/1706.03762 as reference
    sample_paper_xml = """<?xml version="1.0" encoding="UTF-8"?>
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

    # Mock single paper endpoint (using real arXiv ID from reference)
    httpserver.expect_request(
        "/api/query", query_string="id_list=1706.03762&start=0&max_results=1"
    ).respond_with_data(sample_paper_xml, content_type="application/xml")

    # Mock 404 for non-existent paper
    httpserver.expect_request(
        "/api/query", query_string="id_list=9999.99999&start=0&max_results=1"
    ).respond_with_data(
        """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <title>ArXiv Query: search_query=id:9999.99999&amp;id_list=&amp;start=0&amp;max_results=1</title>
  <id>http://arxiv.org/api/query?search_query=id:9999.99999&amp;id_list=&amp;start=0&amp;max_results=1</id>
  <updated>2024-01-15T12:00:00Z</updated>
  <opensearch:totalResults>0</opensearch:totalResults>
  <opensearch:startIndex>0</opensearch:startIndex>
  <opensearch:itemsPerPage>1</opensearch:itemsPerPage>
</feed>""",
        content_type="application/xml",
    )

    # Mock server error
    httpserver.expect_request(
        "/api/query", query_string="id_list=1706.99999&start=0&max_results=1"
    ).respond_with_data("Internal Server Error", status=500, content_type="text/plain")

    return httpserver
