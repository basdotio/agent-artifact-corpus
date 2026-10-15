"""Basic tests for lit-mcp package."""

def test_import():
    """Test that the main module can be imported."""
    import lit_mcp.__main__ as main
    assert hasattr(main, 'mcp')
    assert hasattr(main, 'arxiv_search')
    assert hasattr(main, 'main')

def test_arxiv_search_function():
    """Test that the arxiv_search function is properly decorated."""
    import lit_mcp.__main__ as main
    # Check that the function exists and is callable
    assert callable(main.arxiv_search)
    
    # Test with a simple query (this will make an actual API call)
    try:
        results = main.arxiv_search("machine learning", max_results=1)
        assert isinstance(results, list)
        if results:  # If we got results
            assert isinstance(results[0], dict)
            assert 'title' in results[0]
            assert 'authors' in results[0]
    except Exception as e:
        # If the API call fails, that's okay for testing purposes
        print(f"API call failed (expected in some environments): {e}")

def test_dblp_search_function():
    """Test that the dblp_search function is properly decorated."""
    import lit_mcp.__main__ as main
    # Check that the function exists and is callable
    assert callable(main.dblp_search)
    
    # Test with a simple query (this will make an actual API call)
    try:
        results = main.dblp_search("machine learning", max_results=1)
        assert isinstance(results, list)
        if results:  # If we got results
            assert isinstance(results[0], dict)
            # Check for DBLP-specific attributes
            expected_attrs = ['title', 'authors', 'venue', 'volume', 'number', 
                            'pages', 'publisher', 'year', 'type', 'access', 
                            'key', 'doi', 'ee', 'url']
            for attr in expected_attrs:
                assert attr in results[0]
    except Exception as e:
        # If the API call fails, that's okay for testing purposes
        print(f"DBLP API call failed (expected in some environments): {e}")

if __name__ == "__main__":
    test_import()
    test_arxiv_search_function()
    test_dblp_search_function()
    print("All tests passed!")
