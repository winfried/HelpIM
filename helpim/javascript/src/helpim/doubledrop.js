goog.provide('helpim.DoubleDrop');

goog.require('goog.dom');
goog.require('goog.events');

goog.exportSymbol('helpim.DoubleDrop.start', helpim.DoubleDrop.start);

/**
 * @constructor
 */
helpim.DoubleDrop = function(mainListId, subListId, subLists) {
	this._mainList = goog.dom.getElement(mainListId);
	this._subList = goog.dom.getElement(subListId);
	this._subListOptions = subList;
};

helpim.DoubleDrop.prototype.start = function() {
	goog.events.listen(this._mainList, goog.events.EventType.CHANGE, function(e) {
		var selectedIndex = e.target.selectedIndex;
		
		/* empty second combobox */
		for(var i=0, len=this._subList.children.length; i<len; ++i) {
			this._subList.remove(this._subList.children[i]);
		}
		
		/* fill second combobox with new options */
		for(var i=0, len=this._subListOptions[selectedIndex].length; i<len; ++i) {
			var el = goog.dom.createDom('option', {'value': this._subListOptions[selectedIndex][i], 'text': this._subListOptions[selectedIndex][i]});
			this._subList.add(el, null);
		}
	}, false, this);
};