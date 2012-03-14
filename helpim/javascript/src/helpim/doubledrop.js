goog.provide('helpim.DoubleDrop');

goog.require('goog.dom');
goog.require('goog.events');
goog.require('goog.iter');

goog.exportSymbol('helpim.DoubleDrop', helpim.DoubleDrop);
goog.exportSymbol('helpim.DoubleDrop.start', helpim.DoubleDrop.start);

/**
 * @constructor
 */
helpim.DoubleDrop = function(mainListId, subListId, subLists) {
	this._mainList = goog.dom.getElement(mainListId);
	this._subList = goog.dom.getElement(subListId);
	this._subListOptions = subLists;
};

helpim.DoubleDrop.prototype.start = function() {
	goog.events.listen(this._mainList, goog.events.EventType.CHANGE, function(e) {
		/* empty second combobox */
		goog.dom.removeChildren(this._subList);
		
		/* fill second combobox with new options */
		goog.iter.forEach(this._subListOptions[e.target.selectedIndex], function(opt) {
			var el = goog.dom.createDom('option', {'value': opt}, goog.dom.createTextNode(opt));
			goog.dom.appendChild(this._subList, el);
		}, this);
	}, false, this);
};