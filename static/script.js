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
                .click({id: topics[i]['id']}, selectTopic)
        );
    }
}

var word_distribution = undefined;
function selectTopic(event) {
    var id = event.data.id;
    var topic;

    for (var i = 0; i < topics.length; i++) {
        if (topics[i]['id'] == id) {
            topic = topics[i];
            break;
        }
    }

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
                    .text('Document ' + topic['top_documents'][i])
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
            data: topic['top_word_values'],
            backgroundColor: 'rgba(0, 204, 102, 0.5)',
            borderColor: 'rgba(0, 153, 77, 1)',
            borderWidth: 1
        }],
        labels: topic['top_words']
    };
    console.log(data);

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

function createDocumentElements() {
    var documentList = $('#documents-list');

    for (var i = 0; i < documents.length; i++) {
        documentList
            .append(
                $('<div/>')
                    .addClass('document-name')
                    .attr('id', 'document_' + documents[i])
                    .text('Document ' + documents[i])
                    .click({documentId: documents[i]}, selectDocument)
            )
    }
}

var topic_distribution = undefined;
var valid_colors = ['#0066ff', '#cc0000', '#339933', '#e6e600', '#666699', '#ff9933', '#29a3a3']
function selectDocument(event) {
    var id = event.data.documentId;
    var result_id = window.location.href.split('/').pop();
    
    $.ajax({
        url: '/document_info/',
        type: 'POST',
        dataType: 'json',
        data: {document_id: id, result_id: result_id},
        success: function(document) {
            console.log(document);
            $('.document-name').removeClass('selected');
            $('#document_' + id + '.document-name').addClass('selected');

            $('#document-title').text('Document ' + id);
            $('#document-text').text(document['text']);

            var relatedDocumentsContent = $('#related-topics-content');
            relatedDocumentsContent.empty();
            for (var i = 0; i < document['topics'].length; i++) {
                relatedDocumentsContent
                    .append(
                        $('<span/>')
                            .addClass('topic-link')
                            .text(document['topics'][i]['topic_name'])
                            .click({id: document['topics'][i]['topic_id']}, selectTopic)
                    );

                if (i != document['topics'].length - 1) {
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
            for (var i = 0; i < document['topics'].length; i++) {
                var topicId = document['topics'][i]['topic_id'];
                var val = document['topics'][i]['probability'];
                data.datasets[0].data.push(val);
                data.datasets[0].backgroundColor.push(valid_colors[i % valid_colors.length]);
                data.labels.push(document['topics'][i]['topic_name']);
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
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            console.log(textStatus);
            console.log(errorThrown);
        }
    });
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

            if (topicId == -1) {
                return;
            }

            $.ajax({
                url: '/topic_documents/',
                type: 'POST',
                dataType: 'json',
                data: {topic_id: topicId},
                success: function(response) {
                    console.log(response);
                    $('#documents-list').empty();
                    documents = response['data'];

                    createDocumentElements();
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    console.log(jqXHR);
                    console.log(textStatus);
                    console.log(errorThrown);
                }
            });
        } else {
            var result_id = window.location.href.split('/').pop();
            $.ajax({
                url: '/search_keyword/',
                type: 'POST',
                dataType: 'json',
                data: {result_id: result_id, keyword: query},
                success: function(response) {
                    console.log(response);
                    $('#documents-list').empty();
                    documents = response['data'];

                    createDocumentElements();
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    console.log(jqXHR);
                    console.log(textStatus);
                    console.log(errorThrown);
                }
            });
        }
    }
    $('#documents-search').focus();
    $('#documents-list').animate({ scrollTop: "0" }, 250);
}

function findTopicId(topicName) {
    for (var i = 0; i < topics.length; i++) {
        if (topics[i]['name'] == topicName) {
            return topics[i]['id'];
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

function showUploadModal() {
    $('#upload-modal').css({'display': 'flex'});
}

function showAnalysisModal(corpusId, corpusName) {
    $('#corpus-name').text(corpusName);
    $('#corpus-id-input').val(corpusId);
    $('#analysis-modal').css({'display': 'flex'});
}

function submitAnalysis() {
    $('#analysis-submit').attr('disabled', true);
    var data = {corpus_id: $('#corpus-id-input').val(),
                topic_num: $('#topic-number-input').val(),
                analysis_name: $('#analysis-name-input').val(),            
    }
    $.ajax({
        url: 'analyze/',
        type: 'POST',
        dataType: 'json',
        data: data,
        success: function(response) {
            location.reload();
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            console.log(textStatus);
            console.log(errorThrown);
        }
    });
}

window.onclick = function(event) {
    if (event.target.id == 'upload-modal') {
        $('#upload-modal').hide();
    } else if (event.target.id == 'analysis-modal') {
        $('#analysis-modal').hide();
    }
}

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

$(document).ready(function() {
    var csrftoken = jQuery("[name=csrfmiddlewaretoken]").val();
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });
});