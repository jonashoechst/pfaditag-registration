/**
 * Group Tree Handler
 * Provides functionality for the hierarchical group tree component with search and animation
 */

function initGroupTree(treeData) {
    // Configuration constants
    const ANIMATION_DURATION = 250;
    const SEARCH_DEBOUNCE_MS = 300;
    const TREE_CONTAINER_ID = 'group_tree';
    const GROUP_ID_FIELD = 'group_id';
    const SEARCH_INPUT_ID = 'group_tree_search';

    // State management
    const state = {
        originalTreeData: treeData,
        tree: null,
        searchTimeout: null
    };

    // Cache DOM elements
    const $groupTree = $(`#${TREE_CONTAINER_ID}`);
    const $groupIdField = $(`#${GROUP_ID_FIELD}`);
    const $searchInput = $(`#${SEARCH_INPUT_ID}`);

    // Helper function to filter tree data recursively
    function filterTreeData(nodes, searchText) {
        if (!searchText) return nodes;
        
        const filtered = [];
        const searchLower = searchText.toLowerCase();
        
        for (const node of nodes) {
            const nodeText = node.text.toLowerCase();
            const childrenMatch = node.children ? filterTreeData(node.children, searchText) : [];
            
            // Include node if it matches or has matching children
            if (nodeText.includes(searchLower) || childrenMatch.length > 0) {
                filtered.push({
                    id: node.id,
                    text: node.text,
                    children: childrenMatch
                });
            }
        }
        
        return filtered;
    }

    // Helper function to expand all nodes recursively
    function expandAllNodes(tree, node) {
        if (!node || node.length === 0) return;
        
        tree.expand(node);
        const children = node.find('ul > li');
        children.each(function() {
            expandAllNodes(tree, $(this));
        });
    }

    // Apply animation overrides to tree expand/collapse methods
    function applyAnimationOverrides(tree) {
        const originalExpand = tree.expand;
        const originalCollapse = tree.collapse;
        
        tree.expand = function(node, cascadeSelection, refresh) {
            const ul = node.find('> ul');
            if (ul.length && !ul.is(':visible')) {
                // First call original expand to set up the DOM
                originalExpand.call(tree, node, cascadeSelection, refresh);
                // Then animate the newly visible ul
                const ulAfterExpand = node.find('> ul');
                if (ulAfterExpand.length) {
                    ulAfterExpand.hide().slideDown(ANIMATION_DURATION, function() {
                        // Add select buttons to newly visible nodes
                        addSelectButtons();
                    });
                }
            } else {
                originalExpand.call(tree, node, cascadeSelection, refresh);
                // Still add buttons in case they're missing
                addSelectButtons();
            }
        };
        
        tree.collapse = function(node, cascadeSelection, refresh) {
            const ul = node.find('> ul');
            if (ul.length && ul.is(':visible')) {
                ul.slideUp(ANIMATION_DURATION, function() {
                    originalCollapse.call(tree, node, cascadeSelection, refresh);
                });
            } else {
                originalCollapse.call(tree, node, cascadeSelection, refresh);
            }
        };
    }

    // Add select buttons to tree nodes
    function addSelectButtons() {
        $groupTree.find('li[data-id]').each(function() {
            const $li = $(this);
            const nodeId = $li.attr('data-id');
            
            // Skip if button already exists
            if ($li.find('.node-select-btn').length > 0) {
                return;
            }
            
            // Create select button with Bootstrap styling
            const $selectBtn = $('<button>', {
                'class': 'node-select-btn btn btn-sm btn-outline-secondary rounded-circle',
                'type': 'button',
                'title': 'Auswählen',
                'data-node-id': nodeId,
                'html': '<i class="fa-solid fa-circle-check"></i>'
            });
            
            // Add button to node
            const $wrapper = $li.find('> span, > div').first();
            if ($wrapper.length) {
                $wrapper.css('position', 'relative');
                $selectBtn.css({
                    'position': 'absolute',
                    'right': '5px',
                    'top': '50%',
                    'transform': 'translateY(-50%)',
                    'padding': '2px 8px',
                    'z-index': '10'
                });
                $wrapper.append($selectBtn);
            }
        });
    }
    
    // Handle node selection via button
    function handleNodeSelection(nodeId) {
        const node = state.tree.getNodeById(nodeId);
        if (node && node.length > 0) {
            // Update hidden field
            $groupIdField.val(nodeId);
            
            // Clear all previous selection states
            $groupTree.find('.node-select-btn')
                .removeClass('btn-primary btn-success btn-outline-primary btn-outline-success')
                .addClass('btn-outline-secondary');
            $groupTree.find('li[data-id]')
                .removeClass('active selected-parent transitively-selected');
            
            // Highlight the directly selected node button (green for success/selected)
            const $selectedBtn = $groupTree.find(`.node-select-btn[data-node-id="${nodeId}"]`);
            $selectedBtn.removeClass('btn-outline-secondary').addClass('btn-success');
            
            // Mark the selected node
            node.addClass('selected-parent');
            
            // Expand the selected node to show children (if it has any)
            if (node.find('ul').length > 0 && state.tree.getChildren(node).length > 0) {
                state.tree.expand(node);
            }
            
            // Mark all descendant nodes as transitively selected
            const descendants = node.find('li[data-id]');
            descendants.addClass('transitively-selected');
            
            // Update descendant select buttons to show transitive selection (blue for info)
            descendants.find('.node-select-btn')
                .removeClass('btn-outline-secondary')
                .addClass('btn-primary');
        }
    }

    // Function to build/rebuild the tree
    function buildTree(data) {
        // Destroy existing tree if it exists
        if (state.tree) {
            state.tree.destroy(true);
        }

        // Build tree
        state.tree = $groupTree.tree({
            uiLibrary: 'bootstrap5',
            dataSource: data,
            cascadeSelection: false,
            border: true,
            primaryKey: 'id',
            selectionType: 'single',
            // Disable default selection on click
            select: function(e) {
                e.preventDefault();
                return false;
            }
        });

        // Override node click behavior to only expand/collapse
        $groupTree.off('click', 'li[data-id]');
        $groupTree.on('click', 'li[data-id] > span, li[data-id] > div', function(e) {
            // Prevent selection if clicking on select button
            if ($(e.target).closest('.node-select-btn').length > 0) {
                e.stopPropagation();
                return false;
            }
            
            const $li = $(this).closest('li[data-id]');
            const node = $li;
            
            // Only expand/collapse if node has children
            if (node.find('ul').length > 0) {
                if (state.tree.getChildren(node).length > 0) {
                    if (node.find('ul:visible').length > 0) {
                        state.tree.collapse(node);
                    } else {
                        state.tree.expand(node);
                    }
                }
            }
            
            // Prevent default selection
            e.stopPropagation();
            return false;
        });
        
        // Add select buttons to all nodes
        addSelectButtons();
        
        // Attach click handlers to select buttons
        $groupTree.off('click', '.node-select-btn');
        $groupTree.on('click', '.node-select-btn', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const nodeId = $(this).attr('data-node-id');
            handleNodeSelection(nodeId);
            return false;
        });

        // Apply animation overrides
        applyAnimationOverrides(state.tree);

        // Apply selection from group_id field to tree
        const selectedId = $groupIdField.val();
        if (selectedId) {
            const groupNode = state.tree.getNodeById(selectedId);
            if (groupNode && groupNode.length > 0) {
                // Highlight the corresponding select button (green for selected)
                $groupTree.find(`.node-select-btn[data-node-id="${selectedId}"]`)
                    .removeClass('btn-outline-secondary')
                    .addClass('btn-success');
                
                // Mark the selected node
                groupNode.addClass('selected-parent');
                
                // Mark all descendant nodes as transitively selected
                const descendants = groupNode.find('li[data-id]');
                descendants.addClass('transitively-selected');
                
                // Update descendant select buttons to show transitive selection (blue)
                descendants.find('.node-select-btn')
                    .removeClass('btn-outline-secondary')
                    .addClass('btn-primary');

                // Expand parent nodes to show selection
                let node = groupNode.parent();
                while (node && node.length > 0 && node[0].id !== TREE_CONTAINER_ID) {
                    state.tree.expand(node);
                    node = node.parent();
                }
                
                // Remove any active class from tree nodes
                $groupTree.find('li[data-id]').removeClass('active');
            }
        }

        // Disable tree if group_id is disabled
        const groupIdElement = $groupIdField[0];
        if (groupIdElement && groupIdElement.disabled) {
            state.tree.disableAll();
            // Also disable all select buttons
            $groupTree.find('.node-select-btn').prop('disabled', true);
        }

        return state.tree;
    }

    // Handle search functionality with debouncing
    function handleSearch() {
        const searchText = $searchInput.val();
        
        clearTimeout(state.searchTimeout);
        state.searchTimeout = setTimeout(() => {
            try {
                const filteredData = filterTreeData(state.originalTreeData, searchText);
                buildTree(filteredData);
                
                // If searching, expand all nodes to show results
                if (searchText) {
                    expandAllNodes(state.tree, $groupTree);
                }
            } catch (error) {
                console.error('Error during tree search:', error);
            }
        }, SEARCH_DEBOUNCE_MS);
    }

    // Initialize
    try {
        buildTree(state.originalTreeData);
        $searchInput.on('input', handleSearch);
    } catch (error) {
        console.error('Error initializing group tree:', error);
    }
}

