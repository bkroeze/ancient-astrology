/**
 * Location Autocomplete Component
 * 
 * A reusable, self-contained location search component with:
 * - Debounced input (300ms)
 * - Dropdown results with keyboard navigation
 * - ARIA accessibility attributes
 * - Error handling with manual entry fallback
 * - Vanilla JS (no external dependencies)
 */
class LocationAutocomplete {
  /**
   * Create a new LocationAutocomplete instance.
   * 
   * @param {Object} config - Configuration options
   * @param {string} config.searchInput - CSS selector for the search input element
   * @param {string} [config.resultsContainer] - CSS selector for results container (created if not provided)
   * @param {Function} config.onSelect - Callback when a location is selected: (location) => void
   *   The location object contains: { name, lat, lon, timezone, country, state }
   */
  constructor(config) {
    this.searchInput = document.querySelector(config.searchInput);
    if (!this.searchInput) {
      throw new Error(`LocationAutocomplete: search input not found: ${config.searchInput}`);
    }
    
    this.onSelect = config.onSelect;
    this.resultsContainer = null;
    
    // Debounce timer
    this.debounceTimer = null;
    this.debounceDelay = 300;
    
    // State
    this.results = [];
    this.selectedIndex = -1;
    this.isLoading = false;
    this.isOpen = false;
    this.error = null;
    
    // Bound event handlers (for cleanup)
    this.boundHandleInput = this.handleInput.bind(this);
    this.boundHandleKeydown = this.handleKeydown.bind(this);
    this.boundHandleBlur = this.handleBlur.bind(this);
    this.boundHandleFocus = this.handleFocus.bind(this);
    
    this.init();
  }
  
  /**
   * Initialize the component.
   */
  init() {
    // Set up search input attributes
    this.searchInput.setAttribute('autocomplete', 'off');
    this.searchInput.setAttribute('spellcheck', 'false');
    this.searchInput.setAttribute('aria-autocomplete', 'list');
    this.searchInput.setAttribute('aria-haspopup', 'listbox');
    this.searchInput.setAttribute('aria-expanded', 'false');
    this.searchInput.setAttribute('aria-controls', 'location-autocomplete-listbox');
    
    // Create results container
    this.resultsContainer = this.createResultsContainer();
    
    // Insert after the search input
    this.searchInput.parentNode.insertBefore(
      this.resultsContainer,
      this.searchInput.nextSibling
    );
    
    // Attach event listeners
    this.searchInput.addEventListener('input', this.boundHandleInput);
    this.searchInput.addEventListener('keydown', this.boundHandleKeydown);
    this.searchInput.addEventListener('blur', this.boundHandleBlur);
    this.searchInput.addEventListener('focus', this.boundHandleFocus);
  }
  
  /**
   * Create the results dropdown container.
   * 
   * @returns {HTMLElement}
   */
  createResultsContainer() {
    const container = document.createElement('div');
    container.className = 'location-autocomplete-results';
    container.id = 'location-autocomplete-listbox';
    container.setAttribute('role', 'listbox');
    container.setAttribute('aria-label', 'Location suggestions');
    
    // Styles
    container.style.cssText = `
      position: absolute;
      z-index: 1000;
      background: white;
      border: 1px solid #ccc;
      border-radius: 4px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
      max-height: 300px;
      overflow-y: auto;
      display: none;
      min-width: 100%;
      box-sizing: border-box;
    `;
    
    return container;
  }
  
  /**
   * Handle input event (debounced).
   * 
   * @param {Event} event
   */
  handleInput(event) {
    const query = event.target.value.trim();
    
    // Clear existing timer
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }
    
    // Clear results if query is empty
    if (!query) {
      this.clearResults();
      return;
    }
    
    // Debounce the search
    this.debounceTimer = setTimeout(() => {
      this.search(query);
    }, this.debounceDelay);
  }
  
  /**
   * Handle keyboard navigation.
   * 
   * @param {KeyboardEvent} event
   */
  handleKeydown(event) {
    if (!this.isOpen && event.key !== 'Enter') {
      return;
    }
    
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        this.selectNext();
        break;
        
      case 'ArrowUp':
        event.preventDefault();
        this.selectPrevious();
        break;
        
      case 'Enter':
        event.preventDefault();
        if (this.selectedIndex >= 0 && this.selectedIndex < this.results.length) {
          this.selectResult(this.selectedIndex);
        }
        break;
        
      case 'Escape':
        event.preventDefault();
        this.closeResults();
        break;
        
      case 'Tab':
        // Allow natural tab behavior, just close results
        this.closeResults();
        break;
    }
  }
  
  /**
   * Handle blur event (with delay for click handling).
   * 
   * @param {FocusEvent} event
   */
  handleBlur(event) {
    // Delay to allow click on results to fire first
    setTimeout(() => {
      // Check if focus moved within our results container
      if (!this.resultsContainer.contains(document.activeElement)) {
        this.closeResults();
      }
    }, 200);
  }
  
  /**
   * Handle focus event.
   * 
   * @param {FocusEvent} event
   */
  handleFocus(event) {
    // Show results if we have cached results and input has content
    if (this.results.length > 0 && this.searchInput.value.trim()) {
      this.openResults();
    }
  }
  
  /**
   * Search for locations.
   * 
   * @param {string} query
   */
  async search(query) {
    this.setLoading(true);
    this.clearError();
    
    try {
      const response = await fetch(`/natal/api/location/search/?q=${encodeURIComponent(query)}`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        credentials: 'same-origin', // Include CSRF cookie
      });
      
      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          throw new Error('Please log in to search locations.');
        }
        throw new Error(`Search failed: ${response.statusText}`);
      }
      
      const data = await response.json();
      this.results = data.results || [];
      this.renderResults();
      
    } catch (error) {
      this.showError(error.message || 'Search failed. You can enter location manually.');
      this.results = [];
      this.renderResults();
    } finally {
      this.setLoading(false);
    }
  }
  
  /**
   * Render the results dropdown.
   */
  renderResults() {
    // Clear container
    this.resultsContainer.innerHTML = '';
    
    if (this.error) {
      // Show error message
      const errorEl = document.createElement('div');
      errorEl.className = 'location-autocomplete-error';
      errorEl.textContent = this.error;
      errorEl.style.cssText = `
        padding: 12px;
        color: #666;
        font-size: 14px;
        font-style: italic;
      `;
      this.resultsContainer.appendChild(errorEl);
      this.openResults();
      return;
    }
    
    if (this.results.length === 0) {
      // Show no results message
      const emptyEl = document.createElement('div');
      emptyEl.className = 'location-autocomplete-empty';
      emptyEl.textContent = 'No locations found';
      emptyEl.style.cssText = `
        padding: 12px;
        color: #666;
        font-size: 14px;
      `;
      this.resultsContainer.appendChild(emptyEl);
      this.openResults();
      return;
    }
    
    // Render each result
    this.results.forEach((result, index) => {
      const option = document.createElement('div');
      option.className = 'location-autocomplete-option';
      option.setAttribute('role', 'option');
      option.setAttribute('data-index', index);
      
      // Format display text: "Name, State, Country" or "Name, Country"
      const displayParts = [result.name];
      if (result.state) {
        displayParts.push(result.state);
      }
      if (result.country) {
        displayParts.push(result.country);
      }
      
      option.innerHTML = `
        <span class="location-autocomplete-name">${this.escapeHtml(result.name)}</span>
        ${result.state || result.country ? 
          `<span class="location-autocomplete-detail">${this.escapeHtml([result.state, result.country].filter(Boolean).join(', '))}</span>` : 
          ''}
        <span class="location-autocomplete-coords">${result.lat?.toFixed(4)}, ${result.lon?.toFixed(4)}</span>
      `;
      
      // Styles
      option.style.cssText = `
        padding: 10px 12px;
        cursor: pointer;
        border-bottom: 1px solid #eee;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
      `;
      
      // Hover and selection styles via JS for better control
      option.addEventListener('mouseenter', () => {
        this.setSelectedIndex(index);
      });
      
      option.addEventListener('click', () => {
        this.selectResult(index);
      });
      
      this.resultsContainer.appendChild(option);
    });
    
    // Style the last item to remove border
    const lastOption = this.resultsContainer.lastElementChild;
    if (lastOption) {
      lastOption.style.borderBottom = 'none';
    }
    
    this.openResults();
  }
  
  /**
   * Select a result by index.
   * 
   * @param {number} index
   */
  selectResult(index) {
    if (index < 0 || index >= this.results.length) {
      return;
    }
    
    const result = this.results[index];
    this.closeResults();
    this.searchInput.value = result.name;
    
    // Update aria-activedescendant
    const option = this.resultsContainer.querySelector(`[data-index="${index}"]`);
    if (option) {
      this.searchInput.setAttribute('aria-activedescendant', option.id || `option-${index}`);
    }
    
    // Call the selection callback
    if (this.onSelect) {
      this.onSelect({
        name: result.name,
        lat: result.lat,
        lon: result.lon,
        timezone: result.timezone,
        country: result.country,
        state: result.state,
      });
    }
  }
  
  /**
   * Set the selected index and update UI.
   * 
   * @param {number} index
   */
  setSelectedIndex(index) {
    this.selectedIndex = index;
    this.updateActiveDescendant();
    
    // Update visual selection
    const options = this.resultsContainer.querySelectorAll('.location-autocomplete-option');
    options.forEach((opt, i) => {
      if (i === index) {
        opt.style.backgroundColor = '#e3f2fd';
        opt.style.fontWeight = '500';
      } else {
        opt.style.backgroundColor = '';
        opt.style.fontWeight = '';
      }
    });
    
    // Scroll into view if needed
    const selected = options[index];
    if (selected) {
      selected.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }
  
  /**
   * Select the next result.
   */
  selectNext() {
    if (this.results.length === 0) return;
    
    const newIndex = this.selectedIndex + 1;
    if (newIndex < this.results.length) {
      this.setSelectedIndex(newIndex);
    }
  }
  
  /**
   * Select the previous result.
   */
  selectPrevious() {
    if (this.results.length === 0) return;
    
    const newIndex = this.selectedIndex - 1;
    if (newIndex >= 0) {
      this.setSelectedIndex(newIndex);
    }
  }
  
  /**
   * Update aria-activedescendant attribute.
   */
  updateActiveDescendant() {
    const option = this.resultsContainer.querySelector(`[data-index="${this.selectedIndex}"]`);
    if (option) {
      if (!option.id) {
        option.id = `location-option-${this.selectedIndex}`;
      }
      this.searchInput.setAttribute('aria-activedescendant', option.id);
    }
  }
  
  /**
   * Open the results dropdown.
   */
  openResults() {
    this.isOpen = true;
    this.searchInput.setAttribute('aria-expanded', 'true');
    this.resultsContainer.style.display = 'block';
  }
  
  /**
   * Close the results dropdown.
   */
  closeResults() {
    this.isOpen = false;
    this.selectedIndex = -1;
    this.searchInput.setAttribute('aria-expanded', 'false');
    this.searchInput.removeAttribute('aria-activedescendant');
    this.resultsContainer.style.display = 'none';
  }
  
  /**
   * Clear all results and reset state.
   */
  clearResults() {
    this.results = [];
    this.selectedIndex = -1;
    this.error = null;
    this.resultsContainer.innerHTML = '';
    this.closeResults();
  }
  
  /**
   * Set loading state.
   * 
   * @param {boolean} loading
   */
  setLoading(loading) {
    this.isLoading = loading;
    
    if (loading) {
      this.searchInput.setAttribute('aria-busy', 'true');
      this.searchInput.classList.add('location-autocomplete-loading');
    } else {
      this.searchInput.setAttribute('aria-busy', 'false');
      this.searchInput.classList.remove('location-autocomplete-loading');
    }
  }
  
  /**
   * Show an error message.
   * 
   * @param {string} message
   */
  showError(message) {
    this.error = message;
  }
  
  /**
   * Clear the error state.
   */
  clearError() {
    this.error = null;
  }
  
  /**
   * Escape HTML special characters.
   * 
   * @param {string} text
   * @returns {string}
   */
  escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
  
  /**
   * Clean up event listeners and remove the component.
   */
  destroy() {
    this.searchInput.removeEventListener('input', this.boundHandleInput);
    this.searchInput.removeEventListener('keydown', this.boundHandleKeydown);
    this.searchInput.removeEventListener('blur', this.boundHandleBlur);
    this.searchInput.removeEventListener('focus', this.boundHandleFocus);
    
    // Remove results container
    if (this.resultsContainer && this.resultsContainer.parentNode) {
      this.resultsContainer.parentNode.removeChild(this.resultsContainer);
    }
    
    // Clear references
    this.results = [];
    this.onSelect = null;
  }
}

// Export for module usage (if available) and make available globally
if (typeof module !== 'undefined' && module.exports) {
  module.exports = LocationAutocomplete;
}
