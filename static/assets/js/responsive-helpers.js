/**
 * GetConnects Admin - Responsive Helper Functions
 * Enhances responsive behavior and touch interactions
 */

(function() {
  'use strict';

  /**
   * Mobile Menu Handler
   * Manages sidebar toggle for mobile devices
   */
  function initMobileMenu() {
    const mobileMenuToggle = document.getElementById('mobile-collapse');
    const mobileMenuToggle2 = document.getElementById('mobile-collapse1');
    const navbar = document.querySelector('.pcoded-navbar');
    const body = document.body;

    function toggleMenu(e) {
      if (e) e.preventDefault();
      
      if (navbar) {
        navbar.classList.toggle('mob-open');
        body.classList.toggle('nav-open');
      }
    }

    function closeMenu() {
      if (navbar) {
        navbar.classList.remove('mob-open');
        body.classList.remove('nav-open');
      }
    }

    // Toggle menu on button click
    if (mobileMenuToggle) {
      mobileMenuToggle.addEventListener('click', toggleMenu);
    }
    if (mobileMenuToggle2) {
      mobileMenuToggle2.addEventListener('click', toggleMenu);
    }

    // Close menu when clicking overlay
    body.addEventListener('click', function(e) {
      if (body.classList.contains('nav-open') && !e.target.closest('.pcoded-navbar') && !e.target.closest('#mobile-collapse') && !e.target.closest('#mobile-collapse1')) {
        closeMenu();
      }
    });

    // Close menu on window resize to desktop size
    window.addEventListener('resize', function() {
      if (window.innerWidth > 991) {
        closeMenu();
      }
    });
  }

  /**
   * Touch-Friendly Table Scroll Indicator
   * Shows visual indicators for scrollable tables
   */
  function initTableScrollIndicators() {
    const tables = document.querySelectorAll('.table-responsive');
    
    tables.forEach(function(wrapper) {
      const table = wrapper.querySelector('table');
      if (!table) return;

      function updateScrollIndicator() {
        const hasScroll = wrapper.scrollWidth > wrapper.clientWidth;
        const isAtStart = wrapper.scrollLeft === 0;
        const isAtEnd = wrapper.scrollLeft >= (wrapper.scrollWidth - wrapper.clientWidth - 2);

        wrapper.classList.toggle('has-scroll', hasScroll);
        wrapper.classList.toggle('scroll-start', hasScroll && isAtStart);
        wrapper.classList.toggle('scroll-end', hasScroll && isAtEnd);
        wrapper.classList.toggle('scroll-middle', hasScroll && !isAtStart && !isAtEnd);
      }

      wrapper.addEventListener('scroll', updateScrollIndicator);
      window.addEventListener('resize', updateScrollIndicator);
      updateScrollIndicator();
    });
  }

  /**
   * Enhanced Select All / Deselect All for Multi-selects
   * Provides better UX for multi-select dropdowns
   */
  function enhanceMultiSelects() {
    const multiSelects = document.querySelectorAll('select[multiple].permission-select');
    
    multiSelects.forEach(function(select) {
      // Allow keyboard shortcuts
      select.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + A to select all
        if ((e.ctrlKey || e.metaKey) && e.key === 'a') {
          e.preventDefault();
          for (let i = 0; i < select.options.length; i++) {
            select.options[i].selected = true;
          }
        }
        // Escape to deselect all
        if (e.key === 'Escape') {
          for (let i = 0; i < select.options.length; i++) {
            select.options[i].selected = false;
          }
        }
      });
    });
  }

  /**
   * Responsive Form Validation
   * Ensures form validation messages are visible on mobile
   */
  function enhanceFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(function(form) {
      form.addEventListener('submit', function(e) {
        const invalidFields = form.querySelectorAll(':invalid');
        if (invalidFields.length > 0) {
          // Scroll to first invalid field
          invalidFields[0].scrollIntoView({
            behavior: 'smooth',
            block: 'center'
          });
        }
      });
    });
  }

  /**
   * Touch-friendly Dropdown Improvements
   * Makes dropdowns work better on touch devices
   */
  function enhanceDropdowns() {
    const dropdownToggles = document.querySelectorAll('[data-toggle="dropdown"]');
    
    dropdownToggles.forEach(function(toggle) {
      // Prevent double-tap zoom on iOS
      toggle.addEventListener('touchend', function(e) {
        e.preventDefault();
        toggle.click();
      });
    });
  }

  /**
   * Responsive Modal Adjustments
   * Ensures modals work well on mobile
   */
  function enhanceModals() {
    // When modal opens, prevent body scroll on mobile
    $('.modal').on('show.bs.modal', function() {
      if (window.innerWidth <= 768) {
        document.body.style.position = 'fixed';
        document.body.style.width = '100%';
      }
    });

    // Restore body scroll when modal closes
    $('.modal').on('hidden.bs.modal', function() {
      document.body.style.position = '';
      document.body.style.width = '';
    });
  }

  /**
   * Improve Button Click Feedback
   * Add loading state to buttons
   */
  function enhanceButtonFeedback() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(function(form) {
      form.addEventListener('submit', function(e) {
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn && !submitBtn.disabled) {
          const originalText = submitBtn.textContent;
          submitBtn.disabled = true;
          submitBtn.textContent = 'Loading...';
          
          // Reset if form validation fails
          setTimeout(function() {
            if (!form.checkValidity()) {
              submitBtn.disabled = false;
              submitBtn.textContent = originalText;
            }
          }, 100);
        }
      });
    });
  }

  /**
   * Responsive DataTables Enhancement
   * Improve DataTables behavior on mobile
   */
  function enhanceDataTables() {
    // Add custom styling for DataTables on mobile
    if (window.innerWidth <= 768) {
      $('.dataTables_wrapper').addClass('mobile-view');
    }

    window.addEventListener('resize', function() {
      if (window.innerWidth <= 768) {
        $('.dataTables_wrapper').addClass('mobile-view');
      } else {
        $('.dataTables_wrapper').removeClass('mobile-view');
      }
    });
  }

  /**
   * Sticky Header on Scroll (Mobile)
   * Makes header stick on mobile for better navigation
   */
  function initStickyHeader() {
    const header = document.querySelector('.pcoded-header');
    let lastScroll = 0;

    if (!header) return;

    window.addEventListener('scroll', function() {
      const currentScroll = window.pageYOffset;
      
      if (window.innerWidth <= 991) {
        if (currentScroll > lastScroll && currentScroll > 80) {
          // Scrolling down
          header.style.transform = 'translateY(-100%)';
        } else {
          // Scrolling up
          header.style.transform = 'translateY(0)';
        }
      } else {
        header.style.transform = '';
      }
      
      lastScroll = currentScroll;
    });
  }

  /**
   * Improve Touch Scroll Performance
   * Add momentum scrolling for iOS
   */
  function improveTouchScroll() {
    const scrollableElements = document.querySelectorAll('.table-responsive, .modal-body, .pcoded-navbar');
    
    scrollableElements.forEach(function(el) {
      el.style.webkitOverflowScrolling = 'touch';
    });
  }

  /**
   * Orientation Change Handler
   * Refresh layout on orientation change
   */
  function handleOrientationChange() {
    window.addEventListener('orientationchange', function() {
      // Wait for orientation change to complete
      setTimeout(function() {
        // Trigger resize event for components that need it
        window.dispatchEvent(new Event('resize'));
        
        // Recalculate any DataTables
        if ($.fn.DataTable) {
          $.fn.dataTable.tables({ visible: true, api: true }).columns.adjust();
        }
      }, 100);
    });
  }

  /**
   * Prevent Zoom on Input Focus (iOS)
   * Prevents iOS from zooming in on small input fields
   */
  function preventInputZoom() {
    const inputs = document.querySelectorAll('input, select, textarea');
    
    inputs.forEach(function(input) {
      // Ensure font-size is at least 16px to prevent zoom
      const fontSize = window.getComputedStyle(input).fontSize;
      if (parseFloat(fontSize) < 16) {
        input.style.fontSize = '16px';
      }
    });
  }

  /**
   * Add Loading Spinner Utility
   */
  window.showLoadingSpinner = function(element) {
    if (!element) return;
    element.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"><span class="sr-only">Loading...</span></div>';
  };

  window.hideLoadingSpinner = function(element, originalContent) {
    if (!element) return;
    element.innerHTML = originalContent || '';
  };

  /**
   * Initialize all responsive helpers
   */
  function init() {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init);
      return;
    }

    console.log('Initializing responsive helpers...');

    initMobileMenu();
    initTableScrollIndicators();
    enhanceMultiSelects();
    enhanceFormValidation();
    enhanceDropdowns();
    enhanceModals();
    enhanceButtonFeedback();
    enhanceDataTables();
    initStickyHeader();
    improveTouchScroll();
    handleOrientationChange();
    preventInputZoom();

    console.log('Responsive helpers initialized');
  }

  // Auto-initialize
  init();

})();

