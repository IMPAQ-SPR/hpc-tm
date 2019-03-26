function createTopicElements() {
    var topicsList = $('#topics-list');

    var highest = topics[0]['average_likelihood'];

    for (var i = 0; i < topics.length; i++) {
        var bar_percentage = String(topics[i]['average_likelihood'] / highest * 50 + 50) + '%';
        topicsList.append(
            $('<div/>')
                .addClass('topic-name-container')
                .append(
                    $('<div/>')
                        .addClass('topic-name-bar')
                        .css('width', bar_percentage)
                )
                .append(
                    $('<div/>')
                        .addClass('topic-name')
                        .text(topics[i]['name'])
                )
                .click({id: i}, selectTopic)
        );
    }
}

var word_distribution = undefined;
function selectTopic(event) {
    var id = event.data.id;
    var topic = topics[id];
    $('.topic-name-container').removeClass('selected');
    $('.topic-name-container').eq(id).addClass('selected');

    $('#topic-title').text(topic['name']);
    $('#topic-title-input').off('blur').blur({id: id}, saveTitle);
    $('#average-topic-likelihood').text('Average Likelihood: ' + topic['average_likelihood'].toFixed(5));
    $('#search-related-documents')
        .off('click')
        .click(function() {
            $('#documents-search').val("topic='" + topic['name'] + "'");
            searchDocuments();
        });

    if ($('#topic-container').css('display') == 'none') {
        $('#topics-list').animate({width: '30%'}, 250, function() { $('#topics-list').css('border-right', '1px solid #333333'); });
        $('#topic-container').css({display: 'block'}).animate({width: '70%'}, 250, function() {
            createWordDistChart(topic);
        });

        var highest = topics[0]['average_likelihood'];
        $('.topic-name-bar').each(function(i) {
            var new_percentage = String(topics[i]['average_likelihood'] / highest * 100) + '%';
            $(this).animate({'width': new_percentage}, 250);
        });

        $('.topic-name-container').animate({'border-width': 1}, 250);
        $('.topic-name-container').addClass('shrunken');
    }
    else {
        createWordDistChart(topic);
    }

    var topDocumentsContent = $('#top-documents-content')
    topDocumentsContent.empty()
    for (var i = 0; i < topic['top_documents'].length; i++) {
        topDocumentsContent
            .append(
                $('<span/>')
                    .addClass('document-link')
                    .text(documents[topic['top_documents'][i]]['title'])
                    .click({documentId: topic['top_documents'][i]}, selectDocument)
            );

        if (i != topic['top_documents'].length - 1) {
            topDocumentsContent.append($('<span/>').html(' &#x2022 '));
        }
    }
}

var previousTitle = undefined;

function changeTitle() {
    previousTitle = $('#topic-title').text();
    $('#topic-title-input').val(previousTitle);

    $('#topic-title').hide();
    $('#topic-title-input').css('display', 'inline').select();
    $('#cancel-title-button').css('display', 'inline');
}

function hideNewTitle() {
    previousTitle = undefined;

    $('#topic-title').css('display', 'inline');
    $('#topic-title-input').hide();
    $('#cancel-title-button').hide();
}

function saveTitle(event) {
    var id = event.data.id;
    var newTitle = $('#topic-title-input').val();

    topics[id]['name'] = newTitle;
    $('#topic-title').text(newTitle);
    $('#topics-list .topic-name').eq(id).text(newTitle);

    hideNewTitle();
}

function createWordDistChart(topic) {
    var data = {
        datasets:[{
            data: topic['top_words_values'],
            backgroundColor: 'rgba(0, 204, 102, 0.5)',
            borderColor: 'rgba(0, 153, 77, 1)',
            borderWidth: 1
        }],
        labels: topic['top_words']
    };

    if (word_distribution == undefined) {
        var ctx = $('#word-distribution');
        word_distribution = new Chart(ctx,{
            type: 'bar',
            data: data,
            options: {
                legend: {
                    display: false
                },
                title: {
                    display: true,
                    text: 'Word Distribution'
                },
                scales: {
                    xAxes: [{
                        ticks: {
                            autoSkip: false
                        }
                    }]
                },
                responsive: true,
                maintainAspectRatio: false,
            }
        });
    } else {
        word_distribution.config.data = data;
        word_distribution.update();
    }
}

var docIds = undefined;
function createDocumentElements() {
    var documentList = $('#documents-list');

    for (var i = 0; i < docIds.length; i++) {
        documentList
            .append(
                $('<div/>')
                    .addClass('document-name')
                    .attr('id', 'document_' + docIds[i])
                    .text(documents[docIds[i]]['title'])
                    .click({documentId: docIds[i]}, selectDocument)
            )
    }
}

var topic_distribution = undefined;
var valid_colors = ['#0066ff', '#cc0000', '#339933', '#e6e600', '#666699', '#ff9933', '#29a3a3']
function selectDocument(event) {
    var id = event.data.documentId;
    var document = documents[id];
    $('.document-name').removeClass('selected');
    $('#document_' + id + '.document-name').addClass('selected');

    $('#document-title').text(document['title']);
    $('#document-text').text(document['text']);

    var relatedDocumentsContent = $('#related-topics-content');
    relatedDocumentsContent.empty();
    for (var i = 0; i < document['closest_topics'].length; i++) {
        relatedDocumentsContent
            .append(
                $('<span/>')
                    .addClass('topic-link')
                    .text(topics[document['closest_topics'][i]]['name'])
                    .click({id: document['closest_topics'][i]}, selectTopic)
            );

        if (i != document['closest_topics'].length - 1) {
            relatedDocumentsContent.append($('<span/>').html(' &#x2022 '));
        }
    }

    if ($('#document-container').css('display') == 'none') {
        $('#documents-list-container').animate({width: '30%'}, 250, function() { $('#documents-list-container').css('border-right', '1px solid #333333'); });
        $('#document-container').css({display: 'block'}).animate({width: '70%'}, 250);
    }

    var data = {
        datasets:[{
            data: [],
            backgroundColor: []
        }],
        labels: []
    };

    var sum = 0;
    for (var i = 0; i < document['closest_topics'].length; i++) {
        var topicId = document['closest_topics'][i];
        var val = document['topic_distributions'][topicId];
        data.datasets[0].data.push(val);
        data.datasets[0].backgroundColor.push(valid_colors[i % valid_colors.length]);
        data.labels.push(topics[topicId]['name']);
        sum += val;
    }

    data.datasets[0].data.push(1 - sum);
    data.datasets[0].backgroundColor.push('#b3b3b3');
    data.labels.push('Remaining');

    if (topic_distribution == undefined) {
        var ctx = $('#topic-distribution');
        topic_distribution = new Chart(ctx,{
            type: 'pie',
            data: data
        });
    } else {
        topic_distribution.config.data = data;
        topic_distribution.update();
    }
}

function searchDocuments() {
    var query = $('#documents-search').val().toLowerCase();

    if (query == '') {
        clearSearch();
    } else {
        setExitSearch();
        if (query.slice(0, 6) == 'topic=' && query.charAt(6) == "'" && query.charAt(query.length - 1) == "'") {
            // EXAMPLE: topic='just, like, know'
            var topicName = query.slice(7, -1);
            var topicId = findTopicId(topicName);

            $('.document-name').hide();
            if (topicId == -1) {
                return;
            }
            for (var i = 0; i < docIds.length; i++) {
                if (documents[docIds[i]]['closest_topics'].includes(topicId)) {
                    $('#document_' + docIds[i]).show();
                }
            }
        } else {
            $('.document-name').hide();
            for (var i = 0; i < docIds.length; i++) {
                if (documents[docIds[i]]['title'].toLowerCase().includes(query)) {
                    $('#document_' + docIds[i]).show();
                }
            }
        }
    }
    $('#documents-search').focus();
    $('#documents-list').animate({ scrollTop: "0" }, 250);
}

function findTopicId(topicName) {
    for (var i = 0; i < topics.length; i++) {
        if (topics[i]['name'] == topicName) {
            return i;
        }
    }

    return -1;
}

function clearSearch() {
    $('#documents-search').val('');
    $('.document-name').show();
    setSearchMagnifyingGlass();
    $('#documents-search').focus();
    $('#documents-list').animate({ scrollTop: "0" }, 250);
}

function setSearchMagnifyingGlass() {
    $('#search-button')
        .attr('src', 'templates/search.png')
        .off('click')
        .click(searchDocuments);

    if ($('#documents-search').val() == '') {
        $('.document-name').show();
    }
}

function setExitSearch() {
    $('#search-button')
        .attr('src', 'templates/exit.png')
        .off('click')
        .click(clearSearch);
}

$(document).ready(function() {
    createTopicElements();
    docIds = Object.keys(documents);
    createDocumentElements();
    $('#documents-search-container #search-button').click(searchDocuments);
    $('#documents-search')
        .on('input', setSearchMagnifyingGlass)
        .keypress(function(e) {
            if (e.which == 13) {
                searchDocuments();
            }
        });
});